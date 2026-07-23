from __future__ import annotations

import importlib
from typing import Any

import numpy as np

from motion_edit.generation import omni_contact_graph as omni


# Preserve the eight WBT contact trajectories explicitly:
# heel/toe on both feet, both hemisphere hands, and both knees.
OMNI_KEYPOINT_LINKS_WITH_CONTACT_CORE: dict[str, tuple[str, ...]] = {
    "pelvis": omni.OMNI_KEYPOINT_LINKS["pelvis"],
    "left_hip": omni.OMNI_KEYPOINT_LINKS["left_hip"],
    "left_knee": omni.OMNI_KEYPOINT_LINKS["left_knee"],
    "left_ankle": omni.OMNI_KEYPOINT_LINKS["left_ankle"],
    "left_heel": (
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
    ),
    "left_foot": omni.OMNI_KEYPOINT_LINKS["left_foot"],
    "right_hip": omni.OMNI_KEYPOINT_LINKS["right_hip"],
    "right_knee": omni.OMNI_KEYPOINT_LINKS["right_knee"],
    "right_ankle": omni.OMNI_KEYPOINT_LINKS["right_ankle"],
    "right_heel": (
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_sphere_2_link",
    ),
    "right_foot": omni.OMNI_KEYPOINT_LINKS["right_foot"],
    "torso": omni.OMNI_KEYPOINT_LINKS["torso"],
    "left_shoulder": omni.OMNI_KEYPOINT_LINKS["left_shoulder"],
    "left_elbow": omni.OMNI_KEYPOINT_LINKS["left_elbow"],
    "left_hand": omni.OMNI_KEYPOINT_LINKS["left_hand"],
    "right_shoulder": omni.OMNI_KEYPOINT_LINKS["right_shoulder"],
    "right_elbow": omni.OMNI_KEYPOINT_LINKS["right_elbow"],
    "right_hand": omni.OMNI_KEYPOINT_LINKS["right_hand"],
}

OMNI_SOLVER_POINT_ORDER_WITH_CONTACT_CORE: tuple[str, ...] = (
    "root",
    "torso",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot",
    "right_foot",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_hand",
    "right_hand",
)

OMNI_BODY_EDGES_WITH_CONTACT_CORE: tuple[tuple[str, str], ...] = (
    ("root", "torso"),
    ("root", "left_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("left_ankle", "left_heel"),
    ("left_ankle", "left_foot"),
    ("root", "right_hip"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("right_ankle", "right_heel"),
    ("right_ankle", "right_foot"),
    ("torso", "left_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_hand"),
    ("torso", "right_shoulder"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_hand"),
)

CONTACT_CORE_NAMES: tuple[str, ...] = (
    "left_heel",
    "left_foot",
    "right_heel",
    "right_foot",
    "left_hand",
    "right_hand",
    "left_knee",
    "right_knee",
)

_CONTACT_MASK_ALIASES: dict[str, tuple[str, ...]] = {
    "left_heel": ("left_heel", "LHEE"),
    "left_foot": ("left_toe", "LTOE", "left_foot"),
    "right_heel": ("right_heel", "RHEE"),
    "right_foot": ("right_toe", "RTOE", "right_foot"),
    "left_hand": ("left_hand", "LH"),
    "right_hand": ("right_hand", "RH"),
    "left_knee": ("left_knee", "LK"),
    "right_knee": ("right_knee", "RK"),
}


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


def _semantic_body_weights_with_heels(
    body_names: list[str],
    keypoint_names: list[str],
) -> np.ndarray:
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
            elif (
                "ankle_roll_sphere_1" in name
                or "ankle_roll_sphere_2" in name
                or "heel" in name
            ):
                assign(row, f"{side}_heel")
            elif "ankle_roll_sphere_5" in name or "toe" in name:
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
    """Add independent heel nodes without changing the existing toe/hand/knee API."""

    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    solver = importlib.import_module("motion_edit.contact_laplacian.solver")
    pyroki = importlib.import_module("motion_edit.generation.pyroki_taskspace")

    omni.OMNI_KEYPOINT_LINKS = dict(OMNI_KEYPOINT_LINKS_WITH_CONTACT_CORE)
    omni.OMNI_SOLVER_POINT_ORDER = OMNI_SOLVER_POINT_ORDER_WITH_CONTACT_CORE
    omni.OMNI_BODY_EDGES = OMNI_BODY_EDGES_WITH_CONTACT_CORE
    omni.OMNI_SEMANTIC_WEIGHTS = {
        **omni.OMNI_SEMANTIC_WEIGHTS,
        "left_heel": 8.0,
        "right_heel": 8.0,
    }

    lte.LTE_FULLBODY_KEYPOINT_LINKS.clear()
    lte.LTE_FULLBODY_KEYPOINT_LINKS.update(omni.OMNI_KEYPOINT_LINKS)
    lte.LTE_FULLBODY_CONTACT_NAMES = CONTACT_CORE_NAMES
    lte.LTE_HANDLE_KEYPOINT_NAMES = CONTACT_CORE_NAMES
    lte.CONTACT_BODY_LINK_CANDIDATES["left_heel"] = (
        "left_heel",
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["right_heel"] = (
        "right_heel",
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_sphere_2_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["lhee"] = ("left_heel",)
    lte.CONTACT_BODY_LINK_CANDIDATES["rhee"] = ("right_heel",)
    lte._contact_mask_for_keypoint = _contact_mask_for_keypoint
    lte._semantic_body_weights = _semantic_body_weights_with_heels

    solver._SEMANTIC_BODY_EDGE_CANDIDATES = omni.OMNI_BODY_EDGES

    pyroki.SEMANTIC_LINK_ALIASES.clear()
    pyroki.SEMANTIC_LINK_ALIASES.update(omni.OMNI_KEYPOINT_LINKS)
    pyroki.SEMANTIC_DEFAULT_WEIGHTS.clear()
    pyroki.SEMANTIC_DEFAULT_WEIGHTS.update(omni.OMNI_SEMANTIC_WEIGHTS)
