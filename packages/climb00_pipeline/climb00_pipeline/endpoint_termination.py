"""One next-contact prediction per event; no retry or pose correction."""


def endpoint_failure_reasons(record, *, require_spatial=False, tolerance_cm=4.):
    reasons=[]
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
