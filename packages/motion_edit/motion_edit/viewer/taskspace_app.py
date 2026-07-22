from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from motion_edit.generation.taskspace_spec import (
    ContactAwareTaskspaceMotion,
    read_contact_aware_taskspace_motion,
)


SEMANTIC_EDGES: tuple[tuple[str, str], ...] = (
    ("pelvis", "torso"),
    ("pelvis", "left_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_foot"),
    ("pelvis", "right_hip"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_foot"),
    ("torso", "left_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_hand"),
    ("torso", "right_shoulder"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_hand"),
)

SEMANTIC_BODY_ALIASES: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis",),
    "torso": ("torso_link", "torso"),
    "left_hip": ("left_hip_roll_link", "left_hip_pitch_link"),
    "left_knee": ("left_knee_link",),
    "left_foot": ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    "right_hip": ("right_hip_roll_link", "right_hip_pitch_link"),
    "right_knee": ("right_knee_link",),
    "right_foot": ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
    "left_shoulder": ("left_shoulder_roll_link", "left_shoulder_pitch_link"),
    "left_elbow": ("left_elbow_link",),
    "left_hand": ("left_wrist_yaw_link", "left_rubber_hand_link", "left_sphere_hand_tip_link"),
    "right_shoulder": ("right_shoulder_roll_link", "right_shoulder_pitch_link"),
    "right_elbow": ("right_elbow_link",),
    "right_hand": ("right_wrist_yaw_link", "right_rubber_hand_link", "right_sphere_hand_tip_link"),
}

SEMANTIC_COLORS: dict[str, tuple[int, int, int]] = {
    "pelvis": (245, 205, 80),
    "torso": (245, 205, 80),
    "left_hip": (85, 180, 255),
    "left_knee": (85, 180, 255),
    "left_foot": (85, 180, 255),
    "right_hip": (255, 120, 95),
    "right_knee": (255, 120, 95),
    "right_foot": (255, 120, 95),
    "left_shoulder": (130, 235, 145),
    "left_elbow": (130, 235, 145),
    "left_hand": (130, 235, 145),
    "right_shoulder": (200, 150, 255),
    "right_elbow": (200, 150, 255),
    "right_hand": (200, 150, 255),
}

EDITED_CONTACT_COLOR = np.asarray((255, 90, 90), dtype=np.uint8)
FIXED_CONTACT_COLOR = np.asarray((90, 220, 220), dtype=np.uint8)
ACTUAL_COLOR = np.asarray((235, 235, 235), dtype=np.uint8)
ERROR_COLOR = np.asarray((255, 185, 70), dtype=np.uint8)


@dataclass(frozen=True)
class TaskspaceViewerData:
    frame_start: int
    frame_end: int
    fps: float
    semantic_names: tuple[str, ...]
    semantic_targets_w: np.ndarray
    semantic_colors: np.ndarray
    skeleton_edges: np.ndarray
    contact_targets_w: np.ndarray
    contact_active: np.ndarray
    contact_colors: np.ndarray
    contact_normals_w: np.ndarray
    contact_kinds: tuple[str, ...]
    actual_semantic_w: np.ndarray | None = None
    actual_contact_w: np.ndarray | None = None

    @property
    def frame_count(self) -> int:
        return int(self.frame_end - self.frame_start)


def compile_taskspace_viewer_data(
    spec: ContactAwareTaskspaceMotion,
    *,
    solved_motion: Mapping[str, Any] | None = None,
) -> TaskspaceViewerData:
    spec.validate()
    semantic_names = tuple(spec.semantic_names)
    semantic_targets = np.asarray(spec.semantic_targets_w, dtype=np.float32)
    semantic_colors = np.asarray(
        [SEMANTIC_COLORS.get(name, (180, 180, 180)) for name in semantic_names],
        dtype=np.uint8,
    )
    semantic_index = {name: index for index, name in enumerate(semantic_names)}
    edge_ids = [
        (semantic_index[first], semantic_index[second])
        for first, second in SEMANTIC_EDGES
        if first in semantic_index and second in semantic_index
    ]
    skeleton_edges = np.asarray(edge_ids, dtype=np.int32).reshape(-1, 2)

    contact_slots: list[tuple[Any, int]] = []
    for contact in spec.contacts:
        for point_index in range(np.asarray(contact.points_local).shape[0]):
            contact_slots.append((contact, point_index))
    slot_count = max(1, len(contact_slots))
    contact_targets = np.zeros((spec.frame_count, slot_count, 3), dtype=np.float32)
    contact_active = np.zeros((spec.frame_count, slot_count), dtype=bool)
    contact_colors = np.zeros((slot_count, 3), dtype=np.uint8)
    contact_normals = np.zeros((spec.frame_count, slot_count, 3), dtype=np.float32)
    contact_kinds: list[str] = []

    for slot, (contact, point_index) in enumerate(contact_slots):
        targets = np.asarray(contact.resolved_target_points_w(), dtype=np.float32)
        local_frames = np.asarray(contact.frames, dtype=np.int64) - int(spec.frame_start)
        valid = (local_frames >= 0) & (local_frames < spec.frame_count)
        local_frames = local_frames[valid]
        targets = targets[valid, point_index]
        contact_targets[local_frames, slot] = targets
        contact_active[local_frames, slot] = True
        contact_colors[slot] = EDITED_CONTACT_COLOR if contact.kind == "edited_contact" else FIXED_CONTACT_COLOR
        contact_kinds.append(contact.kind)
        if contact.surface_normal_w is not None:
            normal = np.asarray(contact.surface_normal_w, dtype=np.float32)
            contact_normals[local_frames, slot] = normal[None, :]

    actual_semantic = None
    actual_contact = None
    if solved_motion is not None:
        actual_semantic = _actual_semantic_positions(spec, solved_motion)
        actual_contact = _actual_contact_positions(spec, contact_slots, solved_motion)

    return TaskspaceViewerData(
        frame_start=int(spec.frame_start),
        frame_end=int(spec.frame_end),
        fps=float(spec.fps),
        semantic_names=semantic_names,
        semantic_targets_w=semantic_targets,
        semantic_colors=semantic_colors,
        skeleton_edges=skeleton_edges,
        contact_targets_w=contact_targets,
        contact_active=contact_active,
        contact_colors=contact_colors,
        contact_normals_w=contact_normals,
        contact_kinds=tuple(contact_kinds),
        actual_semantic_w=actual_semantic,
        actual_contact_w=actual_contact,
    )


def run_taskspace_viewer(
    taskspace_spec_path: str | Path,
    *,
    solved_motion_path: str | Path | None = None,
    port: int = 8096,
    loop: bool = True,
) -> None:
    import viser

    spec = read_contact_aware_taskspace_motion(taskspace_spec_path)
    solved_motion = _load_npz(solved_motion_path) if solved_motion_path is not None else None
    data = compile_taskspace_viewer_data(spec, solved_motion=solved_motion)

    server = viser.ViserServer(port=int(port))
    server.gui.configure_theme(control_layout="fixed", control_width="small", dark_mode=True)
    server.scene.add_grid("/taskspace/grid", width=8.0, height=8.0, position=(0.0, 0.0, 0.0))

    trajectory_handles = []
    for index, name in enumerate(data.semantic_names):
        points = data.semantic_targets_w[:, index]
        if points.shape[0] <= 1:
            continue
        color = data.semantic_colors[index]
        trajectory_handles.append(
            server.scene.add_line_segments(
                f"/taskspace/trajectories/{_safe_name(name)}",
                points=np.stack([points[:-1], points[1:]], axis=1),
                colors=np.broadcast_to(color, (points.shape[0] - 1, 2, 3)).copy(),
                line_width=1.5,
                visible=True,
            )
        )

    semantic_points_handle = server.scene.add_point_cloud(
        "/taskspace/current/semantic_targets",
        points=data.semantic_targets_w[0],
        colors=data.semantic_colors,
        point_size=0.045,
        point_shape="circle",
        visible=True,
    )
    skeleton_handle = server.scene.add_line_segments(
        "/taskspace/current/semantic_skeleton",
        points=_skeleton_segments(data.semantic_targets_w[0], data.skeleton_edges),
        colors=np.full((max(1, len(data.skeleton_edges)), 2, 3), 210, dtype=np.uint8),
        line_width=3.0,
        visible=True,
    )
    contact_target_handle = server.scene.add_point_cloud(
        "/taskspace/current/contact_targets",
        points=np.zeros((data.contact_targets_w.shape[1], 3), dtype=np.float32),
        colors=data.contact_colors,
        point_size=0.065,
        point_shape="circle",
        visible=True,
    )
    contact_normal_handle = server.scene.add_arrows(
        "/taskspace/current/contact_normals",
        points=np.zeros((data.contact_targets_w.shape[1], 2, 3), dtype=np.float32),
        colors=np.broadcast_to(data.contact_colors[:, None, :], (data.contact_targets_w.shape[1], 2, 3)).copy(),
        shaft_radius=0.004,
        head_radius=0.012,
        head_length=0.025,
        visible=True,
    )

    actual_semantic_handle = None
    actual_contact_handle = None
    error_handle = None
    if data.actual_semantic_w is not None:
        actual_semantic_handle = server.scene.add_point_cloud(
            "/taskspace/current/actual_semantic",
            points=data.actual_semantic_w[0],
            colors=np.broadcast_to(ACTUAL_COLOR, (len(data.semantic_names), 3)).copy(),
            point_size=0.03,
            point_shape="circle",
            visible=True,
        )
    if data.actual_contact_w is not None:
        actual_contact_handle = server.scene.add_point_cloud(
            "/taskspace/current/actual_contacts",
            points=np.zeros((data.actual_contact_w.shape[1], 3), dtype=np.float32),
            colors=np.broadcast_to(ACTUAL_COLOR, (data.actual_contact_w.shape[1], 3)).copy(),
            point_size=0.04,
            point_shape="circle",
            visible=True,
        )
        error_handle = server.scene.add_line_segments(
            "/taskspace/current/contact_error",
            points=np.zeros((data.actual_contact_w.shape[1], 2, 3), dtype=np.float32),
            colors=np.broadcast_to(ERROR_COLOR, (data.actual_contact_w.shape[1], 2, 3)).copy(),
            line_width=2.0,
            visible=True,
        )

    with server.gui.add_folder("Task-space playback"):
        frame_slider = server.gui.add_slider(
            "Current frame",
            min=0,
            max=max(0, data.frame_count - 1),
            step=1,
            initial_value=0,
        )
        play_button = server.gui.add_button("Play / Pause")
        fps_input = server.gui.add_number("FPS", initial_value=float(data.fps), min=1.0, max=240.0, step=1.0)
        loop_checkbox = server.gui.add_checkbox("Loop", initial_value=bool(loop))
    with server.gui.add_folder("Visibility"):
        show_trajectories = server.gui.add_checkbox("Semantic trajectories", initial_value=True)
        show_targets = server.gui.add_checkbox("Semantic targets", initial_value=True)
        show_contacts = server.gui.add_checkbox("Contact targets", initial_value=True)
        show_actual = server.gui.add_checkbox("Solved motion", initial_value=True)
    with server.gui.add_folder("Diagnostics"):
        diagnostic_text = server.gui.add_markdown("Ready")

    state = {"playing": False, "frame": 0}

    def update_frame(frame: int) -> None:
        index = int(np.clip(frame, 0, max(0, data.frame_count - 1)))
        state["frame"] = index
        semantic = data.semantic_targets_w[index]
        semantic_points_handle.points = semantic
        skeleton_handle.points = _skeleton_segments(semantic, data.skeleton_edges)

        active = data.contact_active[index]
        contact_points = data.contact_targets_w[index].copy()
        contact_points[~active] = np.nan
        contact_target_handle.points = contact_points
        normals = data.contact_normals_w[index]
        normal_segments = np.stack([contact_points, contact_points + normals * 0.12], axis=1)
        contact_normal_handle.points = normal_segments

        semantic_error_text = ""
        if actual_semantic_handle is not None and data.actual_semantic_w is not None:
            actual_semantic_handle.points = data.actual_semantic_w[index]
            errors = np.linalg.norm(data.actual_semantic_w[index] - semantic, axis=-1)
            semantic_error_text = f"  Semantic mean/max: {errors.mean():.4f} / {errors.max():.4f} m"
        contact_error_text = ""
        if actual_contact_handle is not None and error_handle is not None and data.actual_contact_w is not None:
            actual = data.actual_contact_w[index].copy()
            actual[~active] = np.nan
            actual_contact_handle.points = actual
            error_handle.points = np.stack([actual, contact_points], axis=1)
            valid_error = np.linalg.norm(actual[active] - contact_points[active], axis=-1)
            if valid_error.size:
                contact_error_text = f"  Contact mean/max: {valid_error.mean():.4f} / {valid_error.max():.4f} m"
        diagnostic_text.content = (
            f"Frame **{data.frame_start + index}** / {data.frame_end - 1}  "
            f"Active contact points: **{int(active.sum())}**{semantic_error_text}{contact_error_text}"
        )

    @frame_slider.on_update
    def _(_: Any) -> None:
        update_frame(int(frame_slider.value))

    @play_button.on_click
    def _(_: Any) -> None:
        state["playing"] = not state["playing"]

    @show_trajectories.on_update
    def _(_: Any) -> None:
        for handle in trajectory_handles:
            handle.visible = bool(show_trajectories.value)

    @show_targets.on_update
    def _(_: Any) -> None:
        semantic_points_handle.visible = bool(show_targets.value)
        skeleton_handle.visible = bool(show_targets.value)

    @show_contacts.on_update
    def _(_: Any) -> None:
        contact_target_handle.visible = bool(show_contacts.value)
        contact_normal_handle.visible = bool(show_contacts.value)
        if error_handle is not None:
            error_handle.visible = bool(show_contacts.value and show_actual.value)

    @show_actual.on_update
    def _(_: Any) -> None:
        visible = bool(show_actual.value)
        if actual_semantic_handle is not None:
            actual_semantic_handle.visible = visible
        if actual_contact_handle is not None:
            actual_contact_handle.visible = visible
        if error_handle is not None:
            error_handle.visible = bool(visible and show_contacts.value)

    update_frame(0)
    print(f"Task-space viewer: http://localhost:{server.get_port()}")
    print(f"Task-space spec: {Path(taskspace_spec_path).expanduser()}")
    if solved_motion_path is not None:
        print(f"Solved motion overlay: {Path(solved_motion_path).expanduser()}")

    last_tick = time.perf_counter()
    while True:
        time.sleep(0.005)
        if not state["playing"] or data.frame_count <= 1:
            last_tick = time.perf_counter()
            continue
        now = time.perf_counter()
        interval = 1.0 / max(1.0, float(fps_input.value))
        if now - last_tick < interval:
            continue
        last_tick = now
        next_frame = state["frame"] + 1
        if next_frame >= data.frame_count:
            if bool(loop_checkbox.value):
                next_frame = 0
            else:
                next_frame = data.frame_count - 1
                state["playing"] = False
        frame_slider.value = int(next_frame)
        update_frame(next_frame)


def _actual_semantic_positions(
    spec: ContactAwareTaskspaceMotion,
    motion: Mapping[str, Any],
) -> np.ndarray:
    body_pos = _window_motion_array(np.asarray(motion["body_pos_w"], dtype=np.float32), spec)
    body_names = _string_list(motion.get("body_names"))
    positions = np.zeros_like(np.asarray(spec.semantic_targets_w, dtype=np.float32))
    for semantic_index, semantic_name in enumerate(spec.semantic_names):
        body_index = _resolve_body_index(body_names, SEMANTIC_BODY_ALIASES.get(semantic_name, (semantic_name,)))
        if body_index is None:
            positions[:, semantic_index] = np.nan
        else:
            positions[:, semantic_index] = body_pos[:, body_index]
    return positions


def _actual_contact_positions(
    spec: ContactAwareTaskspaceMotion,
    contact_slots: Sequence[tuple[Any, int]],
    motion: Mapping[str, Any],
) -> np.ndarray:
    body_pos = _window_motion_array(np.asarray(motion["body_pos_w"], dtype=np.float32), spec)
    body_quat = _window_motion_array(np.asarray(motion["body_quat_w"], dtype=np.float32), spec)
    body_names = _string_list(motion.get("body_names"))
    slot_count = max(1, len(contact_slots))
    result = np.full((spec.frame_count, slot_count, 3), np.nan, dtype=np.float32)
    for slot, (contact, point_index) in enumerate(contact_slots):
        body_index = _resolve_body_index(body_names, (_label_leaf(contact.body_label), contact.body_label))
        if body_index is None:
            continue
        frames = np.asarray(contact.frames, dtype=np.int64) - int(spec.frame_start)
        valid = (frames >= 0) & (frames < spec.frame_count)
        frames = frames[valid]
        point_local = np.asarray(contact.points_local, dtype=np.float32)[point_index]
        result[frames, slot] = body_pos[frames, body_index] + _quat_apply_wxyz(
            body_quat[frames, body_index],
            np.broadcast_to(point_local, (frames.size, 3)),
        )
    return result


def _window_motion_array(array: np.ndarray, spec: ContactAwareTaskspaceMotion) -> np.ndarray:
    if array.shape[0] == spec.frame_count:
        return array
    if array.shape[0] >= spec.frame_end:
        return array[spec.frame_start : spec.frame_end]
    raise ValueError(
        f"solved motion has {array.shape[0]} frames and cannot cover task-space interval "
        f"[{spec.frame_start}, {spec.frame_end})"
    )


def _skeleton_segments(points: np.ndarray, edges: np.ndarray) -> np.ndarray:
    if edges.size == 0:
        return np.zeros((1, 2, 3), dtype=np.float32)
    return np.stack([points[edges[:, 0]], points[edges[:, 1]]], axis=1).astype(np.float32)


def _resolve_body_index(body_names: Sequence[str], aliases: Sequence[str]) -> int | None:
    lowered = [str(name).lower() for name in body_names]
    for alias in aliases:
        key = _label_leaf(alias).lower()
        if key in lowered:
            return lowered.index(key)
    for alias in aliases:
        key = _label_leaf(alias).lower()
        for index, name in enumerate(lowered):
            if key and (key in name or name in key):
                return index
    return None


def _quat_apply_wxyz(quat: np.ndarray, vector: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float32)
    v = np.asarray(vector, dtype=np.float32)
    qvec = q[..., 1:4]
    uv = np.cross(qvec, v)
    uuv = np.cross(qvec, uv)
    return v + 2.0 * (q[..., :1] * uv + uuv)


def _label_leaf(label: str) -> str:
    return str(label).rstrip("/").split("/")[-1].split(":")[-1]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [str(item) for item in np.asarray(value, dtype=object).reshape(-1).tolist()]


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-", "."} else "_" for char in str(value))


def _load_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="View a generated ContactAwareTaskspaceMotion.")
    parser.add_argument("--taskspace-spec", required=True, type=Path)
    parser.add_argument("--motion", type=Path, default=None, help="Optional solved/canonical motion overlay.")
    parser.add_argument("--port", type=int, default=8096)
    parser.add_argument("--no-loop", action="store_true")
    args = parser.parse_args(argv)
    run_taskspace_viewer(
        args.taskspace_spec,
        solved_motion_path=args.motion,
        port=args.port,
        loop=not args.no_loop,
    )


if __name__ == "__main__":
    main()
