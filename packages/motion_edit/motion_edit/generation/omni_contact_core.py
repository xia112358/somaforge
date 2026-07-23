from __future__ import annotations

import importlib
from typing import Any

import numpy as np

from motion_edit.generation import omni_contact_graph as omni


# Eight physical contact trajectories represented by the two-point foot model:
# heel channels act on ankle semantics, toe channels act on toe semantics.
CONTACT_CORE_NAMES: tuple[str, ...] = (
    "left_ankle",
    "left_foot",
    "right_ankle",
    "right_foot",
    "left_hand",
    "right_hand",
    "left_knee",
    "right_knee",
)

_CONTACT_MASK_ALIASES: dict[str, tuple[str, ...]] = {
    "left_ankle": ("left_heel", "LHEE"),
    "left_foot": ("left_toe", "LTOE", "left_foot"),
    "right_ankle": ("right_heel", "RHEE"),
    "right_foot": ("right_toe", "RTOE", "right_foot"),
    "left_hand": ("left_hand", "LH"),
    "right_hand": ("right_hand", "RH"),
    "left_knee": ("left_knee", "LK"),
    "right_knee": ("right_knee", "RK"),
}

_INSTALLED = False


def _contact_mask_for_keypoint(
    motion: dict[str, Any],
    keypoint: str,
    n_frames: int,
) -> np.ndarray:
    mask = np.zeros(int(n_frames), dtype=bool)
    if "part_order" not in motion or "contact_part_mask" not in motion:
        return mask

    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    part_order = lte._motion_strings(motion, ("part_order",))
    lowered = [str(name).lower() for name in part_order]
    selected: int | None = None
    for candidate in _CONTACT_MASK_ALIASES.get(str(keypoint), (str(keypoint),)):
        candidate_lower = str(candidate).lower()
        if candidate_lower in lowered:
            selected = lowered.index(candidate_lower)
            break
    if selected is None:
        return mask

    raw = np.asarray(motion["contact_part_mask"], dtype=bool)
    if raw.ndim != 2 or selected >= raw.shape[1]:
        return mask
    count = min(int(n_frames), raw.shape[0])
    mask[:count] = raw[:count, selected]
    return mask


def _semantic_body_weights_with_ankle_toe(
    body_names: list[str],
    keypoint_names: list[str],
) -> np.ndarray:
    """Assign every robot body to the ankle+toe Omni semantic graph."""

    weights = np.zeros((len(body_names), len(keypoint_names)), dtype=np.float64)
    semantic = {name: index for index, name in enumerate(keypoint_names)}

    def assign(row: int, name: str) -> None:
        column = semantic.get(name)
        if column is not None:
            weights[row, column] = 1.0

    for row, raw_name in enumerate(body_names):
        name = str(raw_name).lower()
        if name == "world":
            continue
        if name in {"pelvis", "pelvis_contour_link"}:
            assign(row, "pelvis")
        elif name.startswith(("waist", "torso")):
            assign(row, "torso")
        elif name.startswith(("left_", "right_")):
            side = "left" if name.startswith("left_") else "right"
            if "hip" in name:
                assign(row, f"{side}_hip")
            elif "knee" in name:
                assign(row, f"{side}_knee")
            elif any(
                token in name
                for token in (
                    "ankle_roll_sphere_1",
                    "ankle_roll_sphere_2",
                    "heel",
                )
            ):
                # Rear-foot contact is represented by the ankle trajectory.
                assign(row, f"{side}_ankle")
            elif any(
                token in name
                for token in (
                    "ankle_roll_sphere_3",
                    "ankle_roll_sphere_4",
                    "ankle_roll_sphere_5",
                    "toe",
                    "sole",
                    "foot_contact",
                )
            ):
                # Fore-foot contact is represented by the toe endpoint.
                assign(row, f"{side}_foot")
            elif any(token in name for token in ("ankle", "foot")):
                assign(row, f"{side}_ankle")
            elif "shoulder" in name:
                assign(row, f"{side}_shoulder")
            elif "elbow" in name:
                assign(row, f"{side}_elbow")
            elif any(
                token in name
                for token in (
                    "sphere_hand",
                    "rubber_hand",
                    "wrist",
                    "hand",
                    "palm",
                    "finger",
                    "thumb",
                    "pinky",
                )
            ):
                assign(row, f"{side}_hand")
            else:
                assign(row, "torso")
        else:
            assign(row, "pelvis")

    missing = weights.sum(axis=1) <= 0.0
    weights[missing, semantic.get("pelvis", 0)] = 1.0
    return weights / weights.sum(axis=1, keepdims=True)


def install_contact_core_nodes() -> None:
    """Use ankle and toe as the only two foot nodes, both contact-capable."""

    global _INSTALLED
    if _INSTALLED:
        return

    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    solver = importlib.import_module("motion_edit.contact_laplacian.solver")
    pyroki = importlib.import_module("motion_edit.generation.pyroki_taskspace")

    # The base Omni graph already contains knee -> ankle -> toe. Do not add an
    # independent heel vertex. Only change which physical contact channels drive
    # the existing ankle/toe semantic trajectories.
    lte.LTE_FULLBODY_CONTACT_NAMES = CONTACT_CORE_NAMES
    lte.LTE_HANDLE_KEYPOINT_NAMES = CONTACT_CORE_NAMES

    lte.CONTACT_BODY_LINK_CANDIDATES["left_heel"] = (
        "left_ankle",
        "left_foot",  # legacy sparse-proxy fallback
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["right_heel"] = (
        "right_ankle",
        "right_foot",  # legacy sparse-proxy fallback
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_sphere_2_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["left_toe"] = (
        "left_foot",
        "left_ankle_roll_sphere_5_link",
        "left_ankle_roll_sphere_4_link",
        "left_ankle_roll_sphere_3_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["right_toe"] = (
        "right_foot",
        "right_ankle_roll_sphere_5_link",
        "right_ankle_roll_sphere_4_link",
        "right_ankle_roll_sphere_3_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["lhee"] = ("left_ankle", "left_foot")
    lte.CONTACT_BODY_LINK_CANDIDATES["rhee"] = ("right_ankle", "right_foot")
    lte.CONTACT_BODY_LINK_CANDIDATES["ltoe"] = ("left_foot",)
    lte.CONTACT_BODY_LINK_CANDIDATES["rtoe"] = ("right_foot",)

    lte._contact_mask_for_keypoint = _contact_mask_for_keypoint
    lte._semantic_body_weights = _semantic_body_weights_with_ankle_toe

    solver._SEMANTIC_BODY_EDGE_CANDIDATES = omni.OMNI_BODY_EDGES

    # Remove any stale independent-heel aliases from an already-imported process
    # and restore the authoritative Omni ankle/toe/hemisphere-hand mapping.
    pyroki.SEMANTIC_LINK_ALIASES.clear()
    pyroki.SEMANTIC_LINK_ALIASES.update(omni.OMNI_KEYPOINT_LINKS)
    pyroki.SEMANTIC_DEFAULT_WEIGHTS.clear()
    pyroki.SEMANTIC_DEFAULT_WEIGHTS.update(omni.OMNI_SEMANTIC_WEIGHTS)

    _INSTALLED = True
