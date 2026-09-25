"""Default observation manager configurations."""

from holosoma.config_values.wbt.g1.observation import (
    g1_29dof_wbt_a2a_observation,
    g1_29dof_wbt_a2a_pure_observation,
    g1_29dof_wbt_contact_force_observation,
    g1_29dof_wbt_future_ref_observation,
    g1_29dof_wbt_future_ref_no_qdot_observation,
    g1_29dof_wbt_sparse_climb_observation,
    g1_29dof_wbt_observation,
    g1_29dof_wbt_php_student_observation,
    g1_29dof_wbt_php_expert_observation,
)

none = None

DEFAULTS = {
    "none": none,
    "g1_29dof_wbt": g1_29dof_wbt_observation,
    "g1_29dof_wbt_a2a": g1_29dof_wbt_a2a_observation,
    "g1_29dof_wbt_a2a_pure": g1_29dof_wbt_a2a_pure_observation,
    "g1_29dof_wbt_contact_force": g1_29dof_wbt_contact_force_observation,
    "g1_29dof_wbt_future_ref": g1_29dof_wbt_future_ref_observation,
    "g1_29dof_wbt_future_ref_no_qdot": g1_29dof_wbt_future_ref_no_qdot_observation,
    "g1_29dof_wbt_sparse_climb": g1_29dof_wbt_sparse_climb_observation,
    "g1_29dof_wbt_php_student": g1_29dof_wbt_php_student_observation,
    "g1_29dof_wbt_php_expert": g1_29dof_wbt_php_expert_observation,
}
