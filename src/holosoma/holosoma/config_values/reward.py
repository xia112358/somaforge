"""Default reward manager configurations."""

from holosoma.config_values.wbt.g1.reward import (
    g1_29dof_wbt_a2a_reward,
    g1_29dof_wbt_contact_force_reward,
    g1_29dof_wbt_proto_reward,
    g1_29dof_wbt_reward,
)

none = None

DEFAULTS = {
    "none": none,
    "g1_29dof_wbt": g1_29dof_wbt_reward,
    "g1_29dof_wbt_a2a": g1_29dof_wbt_a2a_reward,
    "g1_29dof_wbt_contact_force": g1_29dof_wbt_contact_force_reward,
    "g1_29dof_wbt_proto": g1_29dof_wbt_proto_reward,
}
