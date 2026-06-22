from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import numpy as np

from .contact import contact_graph_from_masks, mask_string, segment_from_contact_transition
from .contact.graph import ContactGraph
from .schema import SegmentRecord

CONTACT_PART_ORDER = ("left_foot", "right_foot", "left_hand", "right_hand", "left_knee", "right_knee")
_CONTACT_PART_ALIASES = {
    "LF": "left_foot",
    "RF": "right_foot",
    "LH": "left_hand",
    "RH": "right_hand",
    "LK": "left_knee",
    "RK": "right_knee",
}
_CONTACT_PART_BODY_CANDIDATES = {
    "left_foot": (
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
        "left_ankle_roll_sphere_3_link",
        "left_ankle_roll_sphere_4_link",
        "left_ankle_roll_sphere_5_link",
        "left_ankle_roll_link",
    ),
    "right_foot": (
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_sphere_2_link",
        "right_ankle_roll_sphere_3_link",
        "right_ankle_roll_sphere_4_link",
        "right_ankle_roll_sphere_5_link",
        "right_ankle_roll_link",
    ),
    "left_hand": ("left_rubber_hand_link", "left_thumb_link", "left_pinky_link", "left_wrist_yaw_link"),
    "right_hand": ("right_rubber_hand_link", "right_thumb_link", "right_pinky_link", "right_wrist_yaw_link"),
    "left_knee": ("left_knee_link",),
    "right_knee": ("right_knee_link",),
}


def _optional_mask(data: np.lib.npyio.NpzFile, key: str) -> np.ndarray | None:
    return np.asarray(data[key], dtype=bool) if key in data else None


def _optional_mask_any(data: np.lib.npyio.NpzFile, keys: tuple[str, ...]) -> np.ndarray | None:
    for key in keys:
        mask = _optional_mask(data, key)
        if mask is not None:
            return mask
    return None


def _optional_indices(data: np.lib.npyio.NpzFile, key: str) -> np.ndarray:
    return np.asarray(data[key], dtype=np.int64) if key in data else np.asarray([], dtype=np.int64)


def _string_array(data: np.lib.npyio.NpzFile, keys: tuple[str, ...]) -> list[str] | None:
    for key in keys:
        if key not in data:
            continue
        values = np.asarray(data[key]).reshape(-1)
        return [str(value.item() if hasattr(value, "item") else value) for value in values]
    return None


def _normalize_contact_part(name: str) -> str:
    return _CONTACT_PART_ALIASES.get(name, name)


def _contact_part_indices(data: np.lib.npyio.NpzFile, width: int | None) -> list[int]:
    raw_names = _string_array(data, ("contact_part_names", "contact_force_part_order", "part_order", "part_names", "contact_body_names"))
    if raw_names is None:
        if width is not None and width < len(CONTACT_PART_ORDER):
            raise ValueError(f"contact mask has {width} columns; expected fixed 6 contact parts")
        return list(range(len(CONTACT_PART_ORDER)))
    normalized = [_normalize_contact_part(name) for name in raw_names]
    missing = [part for part in CONTACT_PART_ORDER if part not in normalized]
    if missing:
        raise ValueError(f"contact part order is missing required parts: {missing}")
    return [normalized.index(part) for part in CONTACT_PART_ORDER]


def _select_contact_parts(mask: np.ndarray | None, indices: list[int]) -> np.ndarray | None:
    if mask is None:
        return None
    arr = np.asarray(mask, dtype=bool)
    if arr.ndim == 1:
        arr = arr.reshape(arr.shape[0], 1)
    if arr.ndim != 2:
        raise ValueError(f"contact mask must be 1D or 2D, got shape={arr.shape}")
    if max(indices, default=-1) >= arr.shape[1]:
        raise ValueError(f"contact mask has {arr.shape[1]} columns; cannot select fixed contact parts")
    return arr[:, indices]


def _contact_part_positions(
    *,
    data: np.lib.npyio.NpzFile,
    body_pos_w: np.ndarray | None,
    part_indices: list[int],
) -> np.ndarray | None:
    if "contact_force_part_position_w" in data:
        arr = np.asarray(data["contact_force_part_position_w"], dtype=float)
        if arr.ndim == 3 and arr.shape[1] >= max(part_indices, default=-1) + 1:
            return arr[:, part_indices, :3]
    if body_pos_w is None:
        return None
    body_names = _string_array(data, ("body_names",))
    if body_names is None:
        return body_pos_w if body_pos_w.shape[1] == len(CONTACT_PART_ORDER) else None
    body_index = {name: index for index, name in enumerate(body_names)}
    part_positions: list[np.ndarray] = []
    for part in CONTACT_PART_ORDER:
        indices = [body_index[name] for name in _CONTACT_PART_BODY_CANDIDATES[part] if name in body_index]
        if not indices:
            part_positions.append(np.full((body_pos_w.shape[0], 3), np.nan, dtype=float))
            continue
        part_positions.append(np.nanmean(body_pos_w[:, indices, :3], axis=1))
    return np.stack(part_positions, axis=1)


class _MaskedMotion(NamedTuple):
    starts: np.ndarray
    ends: np.ndarray
    contact: np.ndarray | None
    active: np.ndarray | None
    support: np.ndarray | None
    body_pos_w: np.ndarray | None
    body_names: list[str] | None


def _load_masked_motion(path: Path) -> _MaskedMotion:
    with np.load(path, allow_pickle=True) as data:
        raw_contact = _optional_mask_any(data, ("contact_part_mask", "contact_force_part_mask"))
        width = raw_contact.shape[1] if raw_contact is not None and raw_contact.ndim == 2 else None
        part_indices = _contact_part_indices(data, width)
        raw_body_pos_w = np.asarray(data["body_pos_w"], dtype=float) if "body_pos_w" in data else None
        part_body_pos_w = _contact_part_positions(data=data, body_pos_w=raw_body_pos_w, part_indices=part_indices)
        return _MaskedMotion(
            starts=_optional_indices(data, "proto_start_idx"),
            ends=_optional_indices(data, "proto_end_idx"),
            contact=_select_contact_parts(raw_contact, part_indices),
            active=_select_contact_parts(_optional_mask_any(data, ("active_part_mask", "active_force_part_mask")), part_indices),
            support=_select_contact_parts(_optional_mask_any(data, ("support_part_mask", "support_force_part_mask")), part_indices),
            body_pos_w=part_body_pos_w,
            body_names=list(CONTACT_PART_ORDER),
        )


def contact_graph_from_masked_motion(path: Path, *, source: str = "force_contact", motion_id: str | None = None) -> ContactGraph:
    inputs = _load_masked_motion(path)
    return contact_graph_from_masks(
        motion_id=motion_id or path.stem,
        proto_starts=inputs.starts,
        proto_ends=inputs.ends,
        contact_mask=inputs.contact,
        active_mask=inputs.active,
        support_mask=inputs.support,
        body_pos_w=inputs.body_pos_w,
        body_names=inputs.body_names,
        source=source,
    )


def segments_from_masked_motion(path: Path, *, source: str = "force_contact", status: str = "candidate", motion_id: str | None = None) -> list[SegmentRecord]:
    inputs = _load_masked_motion(path)
    motion_id = motion_id or path.stem
    graph = contact_graph_from_masks(
        motion_id=motion_id,
        proto_starts=inputs.starts,
        proto_ends=inputs.ends,
        contact_mask=inputs.contact,
        active_mask=inputs.active,
        support_mask=inputs.support,
        body_pos_w=inputs.body_pos_w,
        body_names=inputs.body_names,
        source=source,
    )
    segments: list[SegmentRecord] = []
    for proto_id, transition in enumerate(graph.transitions):
        start_i = transition.start_frame
        end_i = transition.end_frame
        end_frame = max(start_i, end_i - 1)
        segment = segment_from_contact_transition(
            transition=transition,
            segment_id=f"{motion_id}_{source}_{proto_id:04d}",
            source=source,
            status=status,
            track="proto",
            motion_path=str(path),
            clip_npz=str(path),
            clip_output_dir=str(Path("motion_edit/data/exports/clips") / motion_id),
            clip_file_name=path.name,
            atom_label=f"{source}_{proto_id:02d}",
            contact_start=mask_string(inputs.contact[start_i]) if inputs.contact is not None else None,
            contact_end=mask_string(inputs.contact[end_frame]) if inputs.contact is not None else None,
            active=mask_string(inputs.active[start_i]) if inputs.active is not None else None,
            support=mask_string(inputs.support[start_i]) if inputs.support is not None else None,
            events=graph.events,
            anchors=graph.anchors,
            metadata={"proto_index": proto_id},
        )
        segment.validate()
        segments.append(segment)

    if not graph.transitions:
        for proto_id, (start, end) in enumerate(zip(inputs.starts, inputs.ends)):
            start_i = int(start)
            end_i = int(end)
            end_frame = max(start_i, end_i - 1)
            segment = SegmentRecord(
                motion_id=motion_id,
                segment_id=f"{motion_id}_{source}_{proto_id:04d}",
                start_frame=start_i,
                end_frame=end_i,
                source=source,
                status=status,  # type: ignore[arg-type]
                track="proto",
                motion_path=str(path),
                clip_npz=str(path),
                clip_output_dir=str(Path("motion_edit/data/exports/clips") / motion_id),
                clip_file_name=path.name,
                atom_label=f"{source}_{proto_id:02d}",
                contact_start=mask_string(inputs.contact[start_i]) if inputs.contact is not None else None,
                contact_end=mask_string(inputs.contact[end_frame]) if inputs.contact is not None else None,
                active=mask_string(inputs.active[start_i]) if inputs.active is not None else None,
                support=mask_string(inputs.support[start_i]) if inputs.support is not None else None,
                metadata={"proto_index": proto_id},
            )
            segment.validate()
            segments.append(segment)
    return segments
