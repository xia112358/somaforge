"""Shared fail-closed contract for editor, CLI, batch and IK generation."""
from collections.abc import Mapping


def validate_generation_metadata(metadata: Mapping) -> None:
    if metadata.get("augmentation_objective") != "consolidated_v1":
        raise ValueError(
            "Generation requires explicit augmentation_objective=consolidated_v1; "
            "rebuild the plan/taskspace. Legacy or unspecified objectives are retired."
        )
    if metadata.get("free_surface_contacts") is not True:
        raise ValueError(
            "Generation requires free_surface_contacts=True and compiled surface tasks; "
            "rebuild the plan instead of falling back to point-pinned contacts."
        )
