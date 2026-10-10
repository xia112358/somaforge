"""Linearize all already queried signed gaps, including positive clearances.

This is the same geometry used by the existing penalty. Its inactive hinge is
not a substitute for a signed-constraint Jacobian. No proximity cutoff is added.
"""
import numpy as np
from scipy.sparse import coo_matrix


def linearize_signed_geometry(problem, states, records):
    if not records:
        return np.empty(0), coo_matrix((0, states.size)).tocsr()
    fk_jac, fk = problem.pose_derivatives(problem.jnp.asarray(states), problem.rotations)
    fk_jac, fk = np.asarray(fk_jac), np.asarray(fk)
    frames = np.asarray([r[1] for r in records], int)
    a = np.asarray([r[2] for r in records], int)
    local_a = np.asarray([r[3] for r in records])
    b = np.asarray([r[4] for r in records], int)
    local_b = np.asarray([r[5] for r in records])
    normals = np.asarray([r[6] for r in records])
    gaps = np.asarray([r[7] for r in records])
    dimension = states.shape[1]

    def point_derivative(links, local, selected_frames):
        pose, derivative = fk[selected_frames, links], fk_jac[selected_frames, links]
        q, dq = pose[:, :4], np.moveaxis(derivative[:, :4], -1, 1)
        v = np.cross(q[:, 1:], local)
        dv = np.cross(dq[:, :, 1:], local[:, None])
        rotated = 2.*(dq[:, :, :1]*v[:, None]+q[:, None, :1]*dv
            +np.cross(dq[:, :, 1:], v[:, None])+np.cross(q[:, None, 1:], dv))
        result = np.moveaxis(derivative[:, 4:7], -1, 1)+rotated
        result[:, :3] += np.eye(3)[None]
        return result

    jac = point_derivative(a, local_a, frames)
    moving = b >= 0
    if moving.any():
        # A static witness has no pose derivative; self pairs share the root
        # translation, which cancels exactly between the two material points.
        other = point_derivative(b[moving], local_b[moving], frames[moving])
        jac[moving] -= other
    scalar = np.einsum('ni,ndi->nd', normals, jac)
    row, component = np.nonzero(scalar)
    matrix = coo_matrix((scalar[row, component], (row, frames[row]*dimension+component)),
                       shape=(len(records), states.size)).tocsr()
    return gaps, matrix
