from types import SimpleNamespace as NS
import numpy as np
from motion_edit.generation.surface_contact_loss import contact_previous_slots,contact_temporal_residual


def test_slot_reordering_and_no_bridge_across_gap():
    def c(shape,frames):
        return NS(body_label='hand',shape_labels=[shape],metadata={'target_surface_id':'top'},frames=frames,points_local=[[0,0,0]])
    spec=NS(frame_count=4,frame_start=0,contacts=[c('a',[0]),c('b',[0,1]),c('a',[1,3])])
    compiled=NS(contact_weights=np.ones((4,2)),contact_points_local=np.zeros((4,2,3)))
    previous=contact_previous_slots(spec,compiled)
    np.testing.assert_array_equal(previous[1],[1,0])
    assert (previous[3] == -1).all()


def test_steady_correction_preserves_demonstration_motion():
    correction=np.array([[.1,.2,.3]])
    r=contact_temporal_residual(correction,correction,correction,np.ones(1),np.ones(1))
    np.testing.assert_allclose(r,0)
    assert np.linalg.norm(contact_temporal_residual(correction+1,correction,correction,np.ones(1),np.ones(1)))>0
    np.testing.assert_allclose(contact_temporal_residual(correction,np.zeros((1,3)),np.zeros((1,3)),np.zeros(1),np.zeros(1)),0)


def test_repeated_shape_labels_do_not_change_contact_identity():
    a=NS(body_label='foot',shape_labels=['sole'],metadata={'target_surface_id':'top'},frames=[0],points_local=[[0,0,0]])
    b=NS(body_label='foot',shape_labels=['sole','sole'],metadata={'target_surface_id':'top'},frames=[1],points_local=[[0,0,0],[.1,0,0]])
    compiled=NS(contact_weights=np.array([[1.,0.],[1.,1.]]),contact_points_local=np.array([[[0.,0,0],[0,0,0]],[[0.,0,0],[.1,0,0]]]))
    previous=contact_previous_slots(NS(frame_count=2,frame_start=0,contacts=[a,b]),compiled)
    np.testing.assert_array_equal(previous[1],[0,-1])
