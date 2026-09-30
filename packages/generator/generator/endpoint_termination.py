"""One next-contact prediction per event; no retry or pose correction."""


def endpoint_failure_reasons(record, *, require_spatial=False, tolerance_cm=4., require_observed_support=False):
    reasons=[]
    if 'endpoint_contact_retention_valid' in record:
        if record['endpoint_contact_retention_valid'] is None:
            reasons.append('endpoint_contact_evidence_unknown')
        elif record['endpoint_contact_retention_valid'] is not True:
            reasons.append('endpoint_contact_retention_failed')
    if 'support_transition_valid' in record:
        reasons.append('legacy_support_judgment_unknown')
    if require_observed_support:
        from somaforge_core.support_semantics import SUPPORT_ASSESSMENT_SCHEMA
        support = record.get('observed_support', {})
        if (support.get('schema') != SUPPORT_ASSESSMENT_SCHEMA
                or not support.get('load_evidence_complete')):
            reasons.append('actual_support_evidence_unknown')
        elif (not support.get('load_coverage_passed')
                or support.get('stationary_support_status') != 'passed_at_recorded_solve_samples'):
            reasons.append('actual_support_not_verified')
    if not record['task_acceptance']['accepted']:
        reasons.append('task_contact_or_safety')
    if not record.get('own_plan_acceptance', record['task_acceptance'])['accepted']:
        reasons.append('own_contact_or_safety')
    if 'region_plan_acceptance' in record and not record['region_plan_acceptance']['accepted']:
        reasons.append('own_region_or_safety')
    if record.get('persistent_role_consistent') is False:
        reasons.append('persistent_role_without_current_contact')
    if require_spatial:
        error=record.get('own_endpoint_position_rms_cm')
        if error is None or not __import__('math').isfinite(error) or error > tolerance_cm:
            reasons.append('own_spatial_endpoint')
    return reasons
