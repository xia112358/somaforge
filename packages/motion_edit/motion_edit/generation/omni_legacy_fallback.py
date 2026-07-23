from __future__ import annotations

import importlib

from motion_edit.generation import omni_contact_graph as omni


FOOT_LINK_ALIASES: dict[str, tuple[str, ...]] = {
    "left_foot": (
        "left_ankle_roll_sphere_5_link",
        "left_ankle_roll_link",
        "left_ankle_pitch_link",
    ),
    "right_foot": (
        "right_ankle_roll_sphere_5_link",
        "right_ankle_roll_link",
        "right_ankle_pitch_link",
    ),
}


def install_legacy_foot_fallbacks() -> None:
    """Keep toe-first semantics while allowing legacy motions without sphere5 bodies."""

    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    pyroki = importlib.import_module("motion_edit.generation.pyroki_taskspace")

    for semantic, aliases in FOOT_LINK_ALIASES.items():
        omni.OMNI_KEYPOINT_LINKS[semantic] = aliases
        lte.LTE_FULLBODY_KEYPOINT_LINKS[semantic] = aliases
        pyroki.SEMANTIC_LINK_ALIASES[semantic] = aliases
