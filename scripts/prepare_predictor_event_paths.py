"""Split immutable events after whole-path Newton contact-motion acceptance.

Produces accepted/rejected event tables and a content-bound certificate. No
trajectory is synthesized between disconnected events or after a rejection.
Source budgets are empirical geometric pivot budgets, not loaded-slip truth.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from analyze_contact_region_motion import analyze
from generator.support_path_acceptance import SCHEMA, file_evidence
from motion_edit.generation.event_acceptance import materialize_contract, audit_events, runs
from somaforge_core.newton_contact_data import load_contact_labels
from somaforge_core.support_semantics import SUPPORT_ASSESSMENT_SCHEMA, assess_support_path
from somaforge_core.support_evidence import load_support_observations


def json_known(value):
    """Missing contact measurements stay unknown, represented as JSON null."""
    if isinstance(value, dict): return {k:json_known(v) for k,v in value.items()}
    if isinstance(value, list): return [json_known(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value): return None
    return value


def contact_geometry_diagnostics(support, start, end):
    """Geometry diagnostics only; never an observed-support acceptance verdict."""
    coverage = np.zeros(end-start, bool)
    for region in support:
        if region['passed']:
            coverage[region['start']-start:region['end']-start] = True
    reasons = []
    if not coverage.all(): reasons.append('incomplete_geometric_pivot_coverage')
    if any(r['required_keep'] and not r['passed'] for r in support):
        reasons.append('declared_keep_geometry_exceeds_budget_or_unknown')
    return reasons, (np.flatnonzero(~coverage)+start).tolist()


def observed_load_acceptance_reasons(status, *, required=False):
    """Recorded loads are diagnostics unless the task explicitly requires coverage.

    Preserve unloaded/unknown samples; attaching observations must not silently
    introduce a new per-solve physical requirement into event contact acceptance.
    """
    if required and status.get('load_coverage_passed') is not True:
        return ['required_observed_load_coverage_failure_or_unknown']
    return []


def prepare(source_motion, source_labels, motion, labels, events_path, output, support_observations=None,
            *, require_observed_load_coverage=False):
    paths = dict(source_motion=source_motion, source_labels=source_labels,
                 motion=motion, labels=labels, events=events_path)
    source = load_contact_labels(source_motion, source_labels)
    actual = load_contact_labels(motion, labels)
    observations = None
    if support_observations is not None:
        paths['support_observations'] = support_observations
        observations = load_support_observations(motion, support_observations)
    if len(source['contact_part_mask']) != len(actual['contact_part_mask']):
        raise ValueError('Source and candidate must share the event clock')
    contract = materialize_contract(source_motion, source_labels, events_path)
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    contact_report, _ = audit_events(contract, actual['contact_part_mask'], actual['contact_surface'])
    phases = []
    for action in contract['actions']:
        a, b = action['start'], action['end']
        # Continuous source contacts are geometry diagnostics, never new keep
        # intentions or observed load-bearing/static support obligations.
        required = {(r['part'],r['surface']) for r in action['requirements'] if r['kind'] == 'keep'}
        spans = {(a,b,p,s) for p,s in required}
        for p in range(6):
            if any(part == p for _,_,part,_ in spans):
                continue
            for face in np.unique(source['contact_surface'][a:b+1,p]):
                if face < 0: continue
                on = (source['contact_part_mask'][a:b+1,p]
                      & (source['contact_surface'][a:b+1,p] == face))
                for left,right in runs(on):
                    if right-left >= contract['policy']['stable_frames']:
                        spans.add((a+left,a+right-1,p,int(face)))
        phases.extend(dict(event_id=action['id'], start=start, end=end, part=p, surface=s,
                           required_keep=(p,s) in required)
                      for start,end,p,s in sorted(spans))
    source_motion_report = analyze(source_motion, source_labels, phases)
    candidate_motion_report = analyze(motion, labels, phases)
    rows = []
    for event, action in zip(events, contract['actions']):
        checks = [r for r in contact_report['checks'] if r['action'] == action['id']]
        support = []
        for phase, baseline, candidate in zip(phases,source_motion_report['phases'], candidate_motion_report['phases']):
            if candidate['event_id'] != action['id']:
                continue
            budget = baseline.get('source_calibration', {}).get('budget_m')
            path = candidate['region_path_cm']['pivot'] / 100
            # Noise tolerated by the shared event checker does not manufacture
            # missing material-motion measurements.
            passed = (budget is not None and candidate['measurement_complete']
                      and not candidate['actual_off_frames'] and path <= budget)
            support.append(dict(candidate, budget_m=budget, passed=bool(passed),
                                required_keep=phase['required_keep']))
        a,b = action['start'], action['end']
        contact_present = actual['contact_part_mask'][a:b+1].any(axis=1)
        reasons = []
        if not event.get('include_for_infiller', True): reasons.append('excluded_adjustment_or_completion')
        if (not any(r['kind'] in ('establish', 'release') for r in action['requirements'])
                and event.get('terminal_event') != 'settled_pose'):
            reasons.append('no_declared_transfer_or_pose_adjustment')
        if not checks or any(not r['passed'] for r in checks): reasons.append('event_contact_failure')
        # Geometric pivot budgets do not decide physical support or turn source
        # load transfer into a static-foot requirement.
        geometry_reasons, unsupported = contact_geometry_diagnostics(support,a,b)
        support_status = (assess_support_path(observations,a,b) if observations is not None
            else dict(schema=SUPPORT_ASSESSMENT_SCHEMA,load_evidence_complete=False,
                      load_coverage_passed=None,stationary_support_status='unknown_without_same_solve_loads'))
        reasons.extend(observed_load_acceptance_reasons(
            support_status, required=require_observed_load_coverage))
        if not contact_present.all(): reasons.append('whole_robot_contact_loss')
        rows.append(dict(segment_id=action['id'], start_frame=a, end_frame=b,
                         accepted=not reasons, reasons=reasons, contact_geometry=support, contact_checks=checks,
                         geometry_diagnostic_reasons=geometry_reasons,
                         missing_geometric_pivot_step_frames=unsupported, observed_support=support_status,
                         event=event))
    report = dict(schema=SCHEMA, evidence={k:file_evidence(v) for k,v in paths.items()},
                  segments=rows, accepted_count=sum(r['accepted'] for r in rows),
                  rejected_count=sum(not r['accepted'] for r in rows),
                  source_motion_report=source_motion_report,
                  candidate_motion_report=candidate_motion_report,
                  contact_report=contact_report, retained_blocks=contract['retained_blocks'],
                  support_assessment_schema=SUPPORT_ASSESSMENT_SCHEMA,
                  acceptance_scope='reference_event_contact; source geometry and recorded loads diagnostic unless explicitly required',
                  task_requirements=dict(observed_load_coverage=require_observed_load_coverage),
                  force_bearing_slip_status='unknown_without_calibrated_loaded_motion_budget',
                  source_quality_status='not_certified_by_relative_source_budgets',
                  training_ready=False)
    report = json_known(report)
    serialized = json.dumps(report, indent=2, allow_nan=False)
    output.mkdir(parents=True, exist_ok=True)
    certificate = output / 'support_path_acceptance.json'
    with certificate.open('x') as stream: stream.write(serialized)
    for accepted, name in ((True, 'accepted_events.jsonl'), (False, 'rejected_events.jsonl')):
        with (output / name).open('x') as stream:
            for row in rows:
                if row['accepted'] == accepted:
                    event = dict(row['event'], source_path=str(motion.resolve()),
                                 contact_source_path=str(labels.resolve()))
                    stream.write(json.dumps(event) + '\n')
    accepted_events = output / 'accepted_events.jsonl'
    with np.load(labels, allow_pickle=False) as z:
        semantics = json.loads(z['contact_semantics_json'].item())
    with (output / 'manifest.json').open('x') as stream:
        json.dump(dict(support_path_acceptance=[dict(file_evidence(certificate), motion_id=0)],
            newton_runtime=semantics['provenance']['newton_runtime'],
            motion_files=[dict(motion_file=str(motion.resolve()),newton_contact_file=str(labels.resolve()),
                event_segments_file=str(accepted_events.resolve()),
                event_segments_sha256=file_evidence(accepted_events)['sha256'],
                **({'support_observations_file':str(support_observations.resolve()),
                    'support_observations_sha256':file_evidence(support_observations)['sha256']} if observations is not None else {}))],
            training_ready=False, scope='single_motion_reference_path_validation'),stream,indent=2)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('source_motion','source_labels','motion','labels','events','output'):
        parser.add_argument('--'+key.replace('_','-'), type=Path, required=True)
    parser.add_argument('--support-observations', type=Path)
    parser.add_argument('--require-observed-load-coverage', action='store_true',
                        help='Explicitly require positive eligible load at every recorded solve sample; not an event-contact or no-slip definition')
    args = parser.parse_args()
    result = prepare(args.source_motion,args.source_labels,args.motion,args.labels,args.events,args.output,args.support_observations,
                     require_observed_load_coverage=args.require_observed_load_coverage)
    print(json.dumps({k:result[k] for k in ('accepted_count','rejected_count','training_ready')}))
