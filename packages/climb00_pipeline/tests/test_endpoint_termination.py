from climb00_pipeline.endpoint_termination import endpoint_failure_reasons


def event():
    return dict(task_acceptance={'accepted':True},own_plan_acceptance={'accepted':True},
                region_plan_acceptance={'accepted':True},own_endpoint_position_rms_cm=1.)


def test_any_failed_required_check_stops_even_with_valid_contact():
    for key in ('task_acceptance','own_plan_acceptance','region_plan_acceptance'):
        row=event();row[key]['accepted']=False
        assert endpoint_failure_reasons(row)
    assert not endpoint_failure_reasons(event(),require_spatial=True)


def test_spatial_unknown_failure_is_explicit_not_a_contact_redefinition():
    for error in (None,float('nan'),float('inf'),10.):
        row=event();row['own_endpoint_position_rms_cm']=error
        assert endpoint_failure_reasons(row,require_spatial=True)==['own_spatial_endpoint']
        assert not endpoint_failure_reasons(row,require_spatial=False)
