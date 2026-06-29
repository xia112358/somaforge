"""Default command manager configurations."""

from holosoma.config_values.wbt.g1.command import (
    CLIMB00_ORIGINAL_MANIFEST,
    DEFAULT_MOTION_MATCHED_MANIFEST,
    g1_29dof_wbt_climb00_original_command,
    g1_29dof_wbt_command,
)

none = None

DEFAULTS = {
    "none": none,
    "g1_29dof_wbt": g1_29dof_wbt_command,
    "g1_29dof_wbt_climb00_original": g1_29dof_wbt_climb00_original_command,
}
