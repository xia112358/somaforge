"""Sparse SQP of the complete original trajectory objective.

The original residual/Jacobian supply the Gauss-Newton metric. All queried
signed geometry rows become inequalities in one coupled linear subproblem.
Physical joint/root bounds are retained. Merit backtracking re-queries the
complete scene; it does not classify contact or edit trajectories afterward.
"""
import time
from types import SimpleNamespace
import numpy as np
from scipy.linalg import cholesky_banded, cho_solve_banded
from scipy.sparse import csc_matrix, diags, eye, vstack
from scipy.sparse.linalg import splu
from threadpoolctl import threadpool_limits
import clarabel
from .continuous_signed_geometry import linearize_signed_geometry

from .continuous_ik import ContinuousResult
from .continuous_factored_ik import FactoredJointProblem


def violation(refresh):
    return sum(max(0., -record[7]) for record in refresh.constraint_linearizations)


class BandedMetricFactor:
    """Factor the complete SPD metric in its actual pose ordering.

    This keeps every coefficient, including temporal and material coupling.
    It never truncates a phase prefix or solves frames independently.
    """
    def __init__(self, matrix, bandwidth):
        entries = matrix.tocoo()
        lower = entries.row >= entries.col
        row, col = entries.row[lower], entries.col[lower]
        band = np.zeros((bandwidth+1, matrix.shape[0]), dtype=matrix.dtype, order='F')
        band[row-col, col] = entries.data[lower]
        # Small band kernels incur severe thread dispatch overhead with the
        # machine's default BLAS pool. Scope this to the numerical operation;
        # restore the caller's settings for other solvers and physics work.
        with threadpool_limits(limits=1, user_api='blas'):
            self.factor = cholesky_banded(band, lower=True, overwrite_ab=True, check_finite=False)

    def solve(self, rhs):
        with threadpool_limits(limits=1, user_api='blas'):
            return cho_solve_banded((self.factor, True), rhs, check_finite=False)


def factor_metric(matrix, *, band_limit=None):
    """Choose storage from the full matrix structure, preserving its system."""
    row, col = matrix.nonzero()
    bandwidth = int(np.abs(row-col).max(initial=0))
    band_bytes = (bandwidth+1)*matrix.shape[0]*matrix.dtype.itemsize
    sparse_bytes = matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes
    # Narrow trajectory metrics avoid costly generic sparse pivoting. A wide
    # material prefix stays sparse rather than allocating a mostly empty band.
    if (band_limit is None or bandwidth <= band_limit) and band_bytes <= 4*sparse_bytes:
        try:
            return BandedMetricFactor(matrix, bandwidth)
        except np.linalg.LinAlgError:
            # Near numerical singularity, retain the original pivoted solve.
            # No damping, coefficient or physical tolerance is changed.
            pass
    return splu(matrix)


def quadratic_schur(hessian, gradient, geometry, required, lower, upper,
                    geometry_tolerance, bound_tolerance, *, factor=None, band_limit=None):
    """Factor the sparse pose metric once; solve only the small active dual."""
    started = time.monotonic()
    if factor is None:
        factor = factor_metric(hessian, band_limit=band_limit)
    free = factor.solve(-gradient)
    n, count = len(free), len(required)
    all_rows = vstack((geometry, eye(n), -eye(n)), format='csr')
    rhs = np.r_[required, lower, -upper]
    tolerances = np.r_[geometry_tolerance, bound_tolerance, bound_tolerance]
    # Feasibility tolerances certify roundoff; they must not deactivate a
    # boundary that the objective's free step would cross.
    active = np.flatnonzero(rhs-all_rows @ free > 0.).tolist()
    iterations = 0
    solution = free
    dual = np.zeros(len(rhs))
    inverse = None
    factored_rows = 0
    for working_iteration in range(100):
        if not active:
            break
        selected = all_rows[active]
        # The working set only expands. Reuse inverse columns from earlier
        # iterations and solve only the newly added constraints.
        additional = factor.solve(all_rows[active[factored_rows:]].T.toarray())
        inverse = additional if inverse is None else np.concatenate((inverse, additional), axis=1)
        factored_rows = len(active)
        schur = np.asarray(selected @ inverse)
        schur = .5*(schur+schur.T)
        residual = rhs[active]-selected @ free
        dual_scale = 1./np.sqrt(schur.diagonal())
        scaled = dual_scale[:, None]*schur*dual_scale[None, :]
        linear = residual*dual_scale
        # Normalize the dual variable/objective together. An absolute gap
        # tolerance must not dominate a subproblem whose value is near zero.
        objective_scale = np.max(np.abs(linear))
        if objective_scale == 0.:
            raise RuntimeError('Active inequalities have a zero dual right-hand side')
        settings = clarabel.DefaultSettings()
        settings.verbose = False
        settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1.e-10
        settings.static_regularization_constant = settings.dynamic_regularization_delta = 1.e-12
        settings.max_iter = 200
        solver = clarabel.DefaultSolver(csc_matrix(np.triu(scaled)), -linear/objective_scale,
            -eye(len(active), format='csc'), np.zeros(len(active)),
            [clarabel.NonnegativeConeT(len(active))], settings)
        result = solver.solve()
        if str(result.status) != 'Solved':
            raise RuntimeError(f'Active dual failed: {result.status}')
        iterations += result.iterations
        multipliers = dual_scale*objective_scale*np.asarray(result.x)
        solution = free+inverse @ multipliers
        if not np.all(np.isfinite(solution)) or not np.all(np.isfinite(multipliers)):
            raise RuntimeError('Nonfinite active dual solution')
        dual[:] = 0.
        dual[active] = multipliers
        remaining = rhs-all_rows @ solution
        missing = np.flatnonzero(remaining > tolerances)
        if not len(missing):
            break
        additions = [int(index) for index in missing if int(index) not in active]
        if not additions:
            raise RuntimeError(f'Dual subproblem remains infeasible by {remaining.max()}: {result.status}')
        active.extend(additions)
    else:
        raise RuntimeError('Whole-trajectory bound working set did not settle')
    return SimpleNamespace(x=solution, y=-dual, factor=factor,
        info=SimpleNamespace(status='solved_schur_dual', status_val=1, iter=iterations,
                             run_time=time.monotonic()-started))


def solve_constrained_trajectory(joint, rows, initial, lower, upper, refresh, *,
                                 max_nfev=125, progress=None,
                                 problem_class=FactoredJointProblem):
    """Minimize the original full objective with its geometry and pose bounds.

    ``max_nfev`` counts whole-trajectory value evaluations, including rejected
    trials. A final restoration query may be required after a rejected trial.
    Numerical KKT tolerances never define simulation contact or task acceptance.
    """
    if max_nfev < 2:
        raise ValueError('Whole-trajectory constrained IK needs at least two evaluations')
    states = np.asarray(initial, dtype=np.float64).copy()
    refresh.constraint_multipliers = None
    refresh.collect_linearizations = True
    problem = problem_class(joint, states.shape)
    size = states.size
    lo = np.broadcast_to(lower, states.shape).ravel()
    hi = np.broadcast_to(upper, states.shape).ravel()
    if not np.all(np.isfinite(states)) or np.any(lo >= hi):
        raise ValueError('Invalid trajectory initial state or bounds')
    if np.any(states.ravel() < lo) or np.any(states.ravel() > hi):
        raise ValueError('Initial trajectory is outside pose bounds')
    solves = []
    damping = 1.e-3
    penalty = 1.
    if hasattr(refresh, 'stacked_arguments'):
        refresh_arguments = lambda value: refresh.stacked_arguments(value, rows, problem.arguments)
    else:
        refresh_arguments = lambda value: joint.stack(refresh(value, rows))
    problem.set_arguments(joint.stack(rows), refresh=refresh_arguments)
    for iteration in range(max_nfev):
        if problem.evaluations >= max_nfev:
            break
        started = time.monotonic()
        previous_timings = dict(problem.timings)
        flat = states.ravel()
        value = problem.fun(flat)
        cost = .5*np.dot(value, value)
        primal_violation = violation(refresh)
        matrix = problem.jac(flat)
        clearances, constraint = linearize_signed_geometry(problem, states, refresh.constraint_linearizations)
        hessian = (matrix.T @ matrix).tocsc()
        gradient = np.asarray(matrix.T @ value)
        diagonal = hessian.diagonal()
        if np.any(diagonal <= 0.):
            raise ValueError('Original objective has an unobserved pose degree of freedom')
        scale = 1./np.sqrt(diagonal)
        variable_scale = diags(scale)
        scaled_constraint = constraint @ variable_scale
        row_scale = np.sqrt(np.asarray(scaled_constraint.multiply(scaled_constraint).sum(axis=1)).ravel())
        fixed = row_scale <= 1.e-15
        if np.any(clearances[fixed] < 0.):
            raise ValueError('A penetrating pair has no available first-order correction')
        clearances, constraint, row_scale = clearances[~fixed], constraint[~fixed], row_scale[~fixed]
        scaled_constraint = scaled_constraint[~fixed]
        scaled_constraint = diags(1./row_scale) @ scaled_constraint
        accepted = None
        trials = []
        quadratic_seconds = 0.
        starting_evaluations = problem.evaluations
        converged = False
        numerical_stagnation = False
        optimality = complementarity = None
        for retry in range(14):
            if problem.evaluations >= max_nfev:
                break
            metric = (variable_scale @ hessian @ variable_scale + damping*eye(size)).tocsc()
            answer = quadratic_schur(metric,
                scale*gradient, scaled_constraint, -clearances/row_scale,
                (lo-flat)/scale, (hi-flat)/scale, np.full(len(clearances),1.e-9)/row_scale,
                np.full(size, 1.e-9)/scale, band_limit=2*states.shape[1])
            quadratic_seconds += answer.info.run_time
            step = scale*answer.x
            geometry_count = len(clearances)
            stationarity = (scale*gradient + scaled_constraint.T @ answer.y[:geometry_count]
                + answer.y[geometry_count:geometry_count+size]
                - answer.y[geometry_count+size:])
            optimality = float(np.max(np.abs(stationarity)))
            slack = np.r_[clearances/row_scale, (flat-lo)/scale, (hi-flat)/scale]
            finite_slack = np.isfinite(slack)
            complementarity = float(np.max(np.abs(answer.y[finite_slack]*slack[finite_slack]), initial=0.))
            max_violation = float(np.maximum(-clearances, 0.).max(initial=0.))
            if max_violation <= 1.e-8 and optimality <= 1.e-5 and complementarity <= 1.e-5:
                converged = True
                break
            penalty = max(penalty, max(np.abs(answer.y[:len(clearances)]/row_scale), default=0.)+1.)
            merit = cost+penalty*primal_violation
            candidate = np.clip(flat+step, lo, hi)
            step = candidate-flat
            linear_value = value+matrix @ step
            linear_violation = float(np.maximum(-(clearances+constraint @ step), 0.).sum())
            predicted_merit = .5*np.dot(linear_value,linear_value)+penalty*linear_violation
            predicted_reduction = merit-predicted_merit
            reduction_roundoff = 16.*np.finfo(np.float64).eps*max(1., abs(merit), abs(predicted_merit))
            if predicted_reduction < -reduction_roundoff:
                trials.append(dict(damping=damping,
                    predicted_reduction=float(predicted_reduction),
                    rejection='model_not_descent', model_ratio=None))
                damping *= 10.
                continue
            if np.array_equal(candidate, flat) or abs(predicted_reduction) <= reduction_roundoff:
                # A ratio of two unresolved differences can accept roundoff
                # as progress and keep inflating damping. Report failure to
                # resolve a step; this is not a stationarity certificate.
                numerical_stagnation = True
                trials.append(dict(damping=damping,
                    predicted_reduction=float(predicted_reduction),
                    rejection='unresolved_model_reduction', model_ratio=None))
                break
            new_value = problem.fun(candidate)
            new_cost = .5*np.dot(new_value, new_value)
            new_violation = violation(refresh)
            new_merit = new_cost+penalty*new_violation
            ratio = ((merit-new_merit)/predicted_reduction
                     if predicted_reduction > 0. else None)
            trials.append(dict(damping=damping, cost=float(new_cost), violation_m=new_violation,
                               merit=float(new_merit), predicted_reduction=float(predicted_reduction),
                               model_ratio=None if ratio is None else float(ratio)))
            if (ratio is not None and ratio < .1 and new_violation > linear_violation
                    and problem.evaluations < max_nfev):
                # First-order feasible steps can acquire second-order geometry
                # error through FK. Correct this error in the original metric
                # before shrinking the tangent step (the SQP Maratos effect).
                # The original objective and exact merit still decide acceptance.
                corrected_gaps, corrected_matrix = linearize_signed_geometry(
                    problem, candidate.reshape(states.shape), refresh.constraint_linearizations)
                corrected_scaled = corrected_matrix @ variable_scale
                corrected_norm = np.sqrt(np.asarray(
                    corrected_scaled.multiply(corrected_scaled).sum(axis=1)).ravel())
                corrected_fixed = corrected_norm <= 1.e-15
                if np.any(corrected_gaps[corrected_fixed] < 0.):
                    trials[-1]['second_order_correction'] = dict(
                        rejection='no_available_normal_correction')
                    damping *= 10.
                    continue
                corrected_gaps, corrected_scaled, corrected_norm = (
                    corrected_gaps[~corrected_fixed], corrected_scaled[~corrected_fixed],
                    corrected_norm[~corrected_fixed])
                corrected_scaled = diags(1./corrected_norm) @ corrected_scaled
                try:
                    correction = quadratic_schur(metric, np.zeros(size), corrected_scaled,
                        -corrected_gaps/corrected_norm, (lo-candidate)/scale, (hi-candidate)/scale,
                        np.full(len(corrected_gaps),1.e-9)/corrected_norm,
                        np.full(size,1.e-9)/scale, factor=answer.factor)
                except RuntimeError as error:
                    # An optional normal correction can be infeasible within
                    # this trial's bounds. Reject it and reduce the original
                    # step; failures of the primary subproblem still propagate.
                    trials[-1]['second_order_correction'] = dict(
                        rejection='normal_subproblem_failed', reason=str(error))
                    damping *= 10.
                    continue
                quadratic_seconds += correction.info.run_time
                normal_step = scale*correction.x
                # A second-order correction stays subordinate to this trial's
                # tangent step; a large restoration requires a new linearization.
                if np.linalg.norm(correction.x) <= np.linalg.norm(step/scale):
                    corrected_pose = np.clip(candidate+normal_step, lo, hi)
                    corrected_value = problem.fun(corrected_pose)
                    corrected_cost = .5*np.dot(corrected_value, corrected_value)
                    corrected_violation = violation(refresh)
                    corrected_merit = corrected_cost+penalty*corrected_violation
                    corrected_ratio = (merit-corrected_merit)/predicted_reduction
                    trials[-1]['second_order_correction'] = dict(
                        cost=float(corrected_cost), violation_m=corrected_violation,
                        model_ratio=float(corrected_ratio),
                        normal_step_norm=float(np.linalg.norm(normal_step)))
                    if corrected_ratio >= .1:
                        candidate, new_value, new_cost, new_violation, ratio = (
                            corrected_pose, corrected_value, corrected_cost,
                            corrected_violation, corrected_ratio)
                        step = candidate-flat
                else:
                    trials[-1]['second_order_correction'] = dict(
                        rejection='normal_correction_larger_than_tangent')
            if ratio is not None and ratio >= .1:
                accepted = (candidate, new_value, new_cost, new_violation, 1.)
                if ratio > .75:
                    damping = max(damping/3., 1.e-12)
                elif ratio < .25:
                    damping *= 2.
                break
            damping *= 10.
        if accepted is None:
            value = problem.fun(flat)
            row = dict(iteration=iteration, kind='solve_finished', cost=float(cost),
                qp_status=answer.info.status, accepted=False, trials=trials,
                success=converged, status=(1 if converged else -2 if numerical_stagnation
                    else 0 if problem.evaluations >= max_nfev else -1),
                termination=('kkt_stationary' if converged else 'numerical_stagnation'
                    if numerical_stagnation else 'evaluation_budget'
                    if problem.evaluations >= max_nfev else 'step_not_accepted'),
                nfev=problem.evaluations-starting_evaluations+int(iteration == 0),
                optimality=optimality, complementarity=complementarity,
                elapsed_seconds=time.monotonic()-started)
            solves.append(row)
            if progress is not None:
                progress(row, states)
            break
        candidate, value, cost, primal_violation, alpha = accepted
        states = candidate.reshape(states.shape)
        audit = refresh.audits[-1]
        row = dict(iteration=iteration, cost=float(cost), accepted=True, alpha=alpha,
            success=False, status=0, termination='evaluation_budget'
                if problem.evaluations >= max_nfev else 'continue',
            nfev=problem.evaluations-starting_evaluations+int(iteration == 0),
            optimality=optimality, complementarity=complementarity,
            qp_status=answer.info.status, qp_iterations=answer.info.iter,
            qp_seconds=quadratic_seconds, hessian_nonzeros=hessian.nnz,
            queried_geometry_rows=len(clearances), penetrating_geometry_rows=int(np.sum(clearances<0)),
            constant_satisfied_rows=int(fixed.sum()),
            terrain_excess_m=audit['terrain_excess_max_m'], self_overlap_m=audit['self_max_m'],
            primal_violation_m=primal_violation, merit_penalty=penalty, next_damping=damping,
            max_joint_step_rad=float(np.abs(alpha*step.reshape(states.shape)[:, joint.root_dofs:]).max()),
            linearization='exact_sparse_blocks_and_material_phase_prefix',
            solver_profile=dict({key: (value-previous_timings.get(key, 0.)
                if key.endswith('_seconds') or key.endswith('_evaluations') else value)
                for key, value in problem.timings.items()},
                total_seconds=time.monotonic()-started), trials=trials)
        solves.append(row)
        if progress is not None:
            progress(dict(kind='solve_finished', **row), states)
    return ContinuousResult(states, value, solves)
