import tyro
from typing_extensions import Annotated

from holosoma.config_types.experiment import ExperimentConfig
from holosoma.config_values.wbt.g1.experiment import (
    g1_29dof_wbt,
    g1_29dof_wbt_a2a,
    g1_29dof_wbt_a2a_pure,
    g1_29dof_wbt_climb00_proto_distill,
    g1_29dof_wbt_climb00_proto_distill_kl01_origref,
    g1_29dof_wbt_climb00_proto_php_distill,
    g1_29dof_wbt_contact_force,
    g1_29dof_wbt_contact_force_touchdown_lift,
    g1_29dof_wbt_future_ref,
)

DEFAULTS = {
    "g1_29dof_wbt": g1_29dof_wbt,
    "g1_29dof_wbt_a2a": g1_29dof_wbt_a2a,
    "g1_29dof_wbt_a2a_pure": g1_29dof_wbt_a2a_pure,
    "g1_29dof_wbt_climb00_proto_distill": g1_29dof_wbt_climb00_proto_distill,
    "g1_29dof_wbt_climb00_proto_distill_kl01_origref": g1_29dof_wbt_climb00_proto_distill_kl01_origref,
    "g1_29dof_wbt_climb00_proto_php_distill": g1_29dof_wbt_climb00_proto_php_distill,
    "g1_29dof_wbt_contact_force": g1_29dof_wbt_contact_force,
    "g1_29dof_wbt_contact_force_touchdown_lift": g1_29dof_wbt_contact_force_touchdown_lift,
    "g1_29dof_wbt_future_ref": g1_29dof_wbt_future_ref,
}

AnnotatedExperimentConfig = Annotated[
    ExperimentConfig,
    tyro.conf.arg(
        constructor=tyro.extras.subcommand_type_from_defaults(
            {f"exp:{k.replace('_', '-')}": v for k, v in DEFAULTS.items()}
        )
    ),
]
