import tyro
from holosoma.config_types.experiment import ExperimentConfig
from holosoma.config_values.wbt.g1.experiment import (
    g1_29dof_wbt_baseline_29,
    g1_29dof_wbt_baseline_single,
    g1_29dof_wbt_contact_force,
)
from typing_extensions import Annotated

DEFAULTS = {
    "g1_29dof_wbt_baseline_single": g1_29dof_wbt_baseline_single,
    "g1_29dof_wbt_baseline_29": g1_29dof_wbt_baseline_29,
    "g1_29dof_wbt_contact_force": g1_29dof_wbt_contact_force,
}

AnnotatedExperimentConfig = Annotated[
    ExperimentConfig,
    tyro.conf.arg(
        constructor=tyro.extras.subcommand_type_from_defaults(
            {f"exp:{key.replace('_', '-')}": value for key, value in DEFAULTS.items()}
        )
    ),
]
