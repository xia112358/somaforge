import numpy as np
from motion_edit.generation.lte_fullbody import _contact_laplacian_evaluation_summary


def test_empty_fixed_handles_are_not_zero_drift_evidence():
    # No handles means no FK calls; the provider itself is intentionally unused.
    q=np.zeros((2,3))
    report=_contact_laplacian_evaluation_summary(q_before=q,q_after=q,provider=None,
        handles=[],semantic_points=('root',))
    assert report['fixed_contact_drift_status']=='not_applicable'
    assert report['fixed_contact_sample_count']==0
    assert report['fixed_contact_drift_max'] is None
