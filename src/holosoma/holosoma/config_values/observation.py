"""Default observation manager configurations."""

from holosoma.config_values.wbt.g1.observation import (
    g1_29dof_wbt_a2a_observation,
    g1_29dof_wbt_a2a_pure_observation,
    g1_29dof_wbt_contact_force_observation,
    g1_29dof_wbt_future_ref_observation,
    g1_29dof_wbt_observation,
)

none = None

DEFAULTS = {
    "none": none,
    "g1_29dof_wbt": g1_29dof_wbt_observation,
    "g1_29dof_wbt_a2a": g1_29dof_wbt_a2a_observation,
    "g1_29dof_wbt_a2a_pure": g1_29dof_wbt_a2a_pure_observation,
    "g1_29dof_wbt_contact_force": g1_29dof_wbt_contact_force_observation,
    "g1_29dof_wbt_future_ref": g1_29dof_wbt_future_ref_observation,
}
