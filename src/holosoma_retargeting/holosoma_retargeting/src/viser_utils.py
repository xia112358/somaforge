# viser_utils.py
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from typing import Callable, List, Tuple

import numpy as np
import viser  # type: ignore[import-not-found]
from viser.extras import ViserUrdf  # type: ignore[import-not-found]


def create_motion_control_sliders(
    server: viser.ViserServer,
    viser_robot: ViserUrdf,
    robot_base_frame: viser.FrameHandle,
    motion_sequence: np.ndarray,
    *,
    robot_dof: int,
    viser_object: ViserUrdf | None = None,
    object_base_frame: viser.FrameHandle | None = None,
    contains_object_in_qpos: bool = True,
    initial_fps: int = 30,
    initial_interp_mult: int = 2,
    loop: bool = True,
    motion_name: str = "motion",
    segment_export_path: str = "data/motion_viewer/segments/motion.segments.jsonl",
    source_motion_npz: str = "",
    motion_npz_data: dict[str, np.ndarray] | None = None,
    clip_output_dir: str = "data/motion_viewer/clips/motion",
    timeline_wrapper: bool = False,
    timeline_port: int = 8090,
    viser_url: str = "http://localhost:8080",
    show_meshes: bool | None = None,
    set_show_meshes: Callable[[bool], None] | None = None,
    contact_force: np.ndarray | None = None,
    contact_force_mask: np.ndarray | None = None,
    contact_force_order: list[str] | None = None,
    contact_force_positions: np.ndarray | None = None,
    contact_force_npz: str | None = None,
    contact_force_npz_data: dict[str, np.ndarray | list[str]] | None = None,
    contact_force_scale: float = 0.003,
    original_motion_paths: list[str] | None = None,
    load_motion_npz: Callable[[str], tuple[np.ndarray, int, str, dict[str, np.ndarray]]] | None = None,
    resolve_segment_export_path: Callable[[str], str] | None = None,
    resolve_clip_output_dir: Callable[[str], str] | None = None,
    resolve_contact_force_npz: Callable[[str], str | None] | None = None,
    load_contact_force_npz: Callable[[str, int], dict[str, np.ndarray | list[str]]] | None = None,
    set_object_for_motion: Callable[[str], tuple[ViserUrdf | None, viser.FrameHandle | None]] | None = None,
    get_object_state: Callable[[], dict[str, str]] | None = None,
) -> Tuple[List[viser.GuiInputHandle[int]], List[float]]:
    """
    Create a slider + play/pause controls and a background player thread with smooth, slerp-based interpolation.

    Assumed qpos layout per frame (MuJoCo order):
        [0:3]   robot base position   (xyz)
        [3:7]   robot base quaternion (wxyz)
        [7:7+R] robot joints          (R = robot_dof)
        [-7:-4] object position  (xyz)            # only if contains_object_in_qpos and viser_object provided
        [-4:]   object quaternion (wxyz)          # only if contains_object_in_qpos and viser_object provided

    Args:
        server: Viser server.
        viser_robot: ViserUrdf for the robot.
        robot_base_frame: server.scene.add_frame(...) return for the robot root frame (we set wxyz/position here).
        motion_sequence: np.ndarray with shape [T, D], sequence of qpos frames.
        robot_dof: number of actuated joints expected by viser_robot.
        viser_object: optional ViserUrdf for an object.
        object_base_frame: optional frame handle for the object root.
        contains_object_in_qpos: set True if motion_sequence includes the object 7D pose at the end.
        initial_fps: base FPS for playback.
        initial_interp_mult: visual upsampling multiplier.
        loop: whether to wrap around at the end.

    Returns:
        (controls, initial_values) — currently returns the [frame_slider] and [0.0]
    """
    qpos = motion_sequence
    n_frames = int(qpos.shape[0])
    if n_frames == 0:
        raise ValueError("motion_sequence is empty.")

    has_object_input = (
        viser_object is not None
        and object_base_frame is not None
        and contains_object_in_qpos
        and qpos.shape[1] >= (7 + robot_dof + 7)
    )
    has_contact_force = (
        contact_force is not None
        and contact_force_mask is not None
        and contact_force.ndim == 3
        and contact_force.shape[0] == n_frames
        and contact_force.shape[-1] == 3
        and contact_force_mask.shape == contact_force.shape[:2]
    )
    if has_contact_force:
        contact_force = np.asarray(contact_force, dtype=np.float32)
        contact_force_mask = np.asarray(contact_force_mask, dtype=bool)
        contact_force_order = contact_force_order or [f"P{i}" for i in range(contact_force.shape[1])]
        if contact_force_positions is not None:
            contact_force_positions = np.asarray(contact_force_positions, dtype=np.float32)
            if contact_force_positions.shape != contact_force.shape:
                contact_force_positions = None
    else:
        contact_force = None
        contact_force_mask = None
        contact_force_order = None
        contact_force_positions = None

    contact_force_magnitude = (
        np.linalg.norm(contact_force, axis=-1).astype(np.float32) if contact_force is not None else None
    )
    contact_force_max = float(np.max(contact_force_magnitude)) if contact_force_magnitude is not None else 0.0
    contact_force_colors = np.asarray(
        [
            [85, 180, 255],
            [255, 120, 95],
            [130, 235, 145],
            [245, 205, 80],
            [200, 150, 255],
            [255, 150, 210],
        ],
        dtype=np.uint8,
    )

    def _contact_colors(n_parts: int) -> np.ndarray:
        repeats = int(np.ceil(max(1, n_parts) / contact_force_colors.shape[0]))
        return np.tile(contact_force_colors, (repeats, 1))[:n_parts]
    force_line_handle = None
    force_point_handle = None
    if contact_force is not None:
        n_parts = int(contact_force.shape[1])
        force_line_handle = server.scene.add_line_segments(
            "/contact_forces/vectors",
            points=np.zeros((n_parts, 2, 3), dtype=np.float32),
            colors=np.repeat(_contact_colors(n_parts)[:, None, :], 2, axis=1),
            line_width=4.0,
            visible=True,
        )
        force_point_handle = server.scene.add_point_cloud(
            "/contact_forces/points",
            points=np.zeros((n_parts, 3), dtype=np.float32),
            colors=_contact_colors(n_parts),
            point_size=0.045,
            point_shape="circle",
            visible=True,
        )

    # ---------------- GUI / state controls ----------------
    class _ValueBox:
        def __init__(self, value):
            self.value = value

        def on_update(self, fn):
            return fn

    class _ButtonBox:
        def on_click(self, fn):
            return fn

    if timeline_wrapper:
        frame_slider = _ValueBox(0)
        clip_start_slider = _ValueBox(0)
        clip_end_slider = _ValueBox(max(1, n_frames))
        play_btn = _ButtonBox()
        set_start_btn = _ButtonBox()
        set_end_btn = _ButtonBox()
        reset_clip_btn = _ButtonBox()
        loop_clip_cb = _ValueBox(bool(loop))
        fps_in = _ValueBox(int(initial_fps))
        atom_label_in = _ValueBox(1)
        segment_index_in = _ValueBox(0)
        save_segment_btn = _ButtonBox()
        load_segment_btn = _ButtonBox()
        interp_mult_in = _ValueBox(int(initial_interp_mult))
    else:
        with server.gui.add_folder("Clip Playback"):
            frame_slider = server.gui.add_slider(
                "Current frame",
                min=0,
                max=max(0, n_frames - 1),
                step=1,
                initial_value=0,
            )
            clip_start_slider = server.gui.add_slider(
                "Start frame",
                min=0,
                max=max(0, n_frames - 1),
                step=1,
                initial_value=0,
            )
            clip_end_slider = server.gui.add_slider(
                "End frame exclusive",
                min=1,
                max=max(1, n_frames),
                step=1,
                initial_value=max(1, n_frames),
            )
            play_btn = server.gui.add_button("Play / Pause")
            set_start_btn = server.gui.add_button("Set start = current")
            set_end_btn = server.gui.add_button("Set end = current + 1")
            reset_clip_btn = server.gui.add_button("Reset clip")
            loop_clip_cb = server.gui.add_checkbox("Loop clip", initial_value=bool(loop))
            fps_in = server.gui.add_number("FPS", initial_value=int(initial_fps), min=1, max=240, step=1)
        atom_label_in = _ValueBox(1)
        segment_index_in = _ValueBox(0)
        save_segment_btn = _ButtonBox()
        load_segment_btn = _ButtonBox()
        with server.gui.add_folder("Smoothing"):
            interp_mult_in = server.gui.add_number(
                "Visual FPS multiplier", initial_value=int(initial_interp_mult), min=1, max=8, step=1
            )

    # ---------------- helpers ----------------
    def _quat_normalize(q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, float)
        n = float(np.linalg.norm(q))
        return q if n == 0.0 else q / n

    def _quat_continuous(prev_q: np.ndarray | None, curr_q: np.ndarray) -> np.ndarray:
        q = _quat_normalize(curr_q)
        if prev_q is None:
            return q
        return -q if float(np.dot(prev_q, q)) < 0.0 else q

    def _slerp(q0: np.ndarray, q1: np.ndarray, u: float) -> np.ndarray:
        q0 = _quat_normalize(q0)
        q1 = _quat_normalize(q1)
        dot = float(np.dot(q0, q1))
        if dot < 0.0:
            q1 = -q1
            dot = -dot
        if dot > 0.9995:
            q = q0 + u * (q1 - q0)
            return _quat_normalize(q)
        theta = np.arccos(np.clip(dot, -1.0, 1.0))
        s = np.sin(theta)
        return (np.sin((1.0 - u) * theta) * q0 + np.sin(u * theta) * q1) / s

    def _interp_frame(qpos_arr: np.ndarray, i0: int, i1: int, u: float) -> np.ndarray:
        """SLERP for base & (optional) object quats; linear for positions and joints."""
        q0 = qpos_arr[i0]
        q1 = qpos_arr[i1]
        out = q0.copy()

        # Robot base (MuJoCo order: pos first, then quat)
        out[0:3] = (1.0 - u) * q0[0:3] + u * q1[0:3]  # pos (xyz)
        out[3:7] = _slerp(q0[3:7], q1[3:7], u)  # quat (wxyz)

        # Joints
        j0 = q0[7 : 7 + robot_dof]
        j1 = q1[7 : 7 + robot_dof]
        out[7 : 7 + robot_dof] = (1.0 - u) * j0 + u * j1

        # Object (optional) (MuJoCo order: pos first, then quat)
        if has_object_input:
            out[-7:-4] = (1.0 - u) * q0[-7:-4] + u * q1[-7:-4]  # obj pos (xyz)
            out[-4:] = _slerp(q0[-4:], q1[-4:], u)  # obj quat (wxyz)
        return out

    # ---------------- state ----------------
    playing = {"flag": False}
    show_meshes_state = {"value": bool(show_meshes) if show_meshes is not None else None}
    tick = {"next": time.perf_counter()}  # absolute time for next draw
    prev: dict[str, np.ndarray | None] = {"robot_q": None, "obj_q": None}  # for continuity
    nonlocal_f = {"f": float(frame_slider.value)}  # fractional frame cursor
    updating_programmatically = {"flag": False}  # flag to prevent callback from pausing during programmatic updates
    segments: list[dict[str, object]] = []
    selected_segment_id = {"value": ""}
    selected_clip_path = {"value": ""}
    last_delete_result: dict[str, object] = {"value": None}

    def _clip_start() -> int:
        return int(np.clip(int(clip_start_slider.value), 0, max(0, n_frames - 1)))

    def _clip_end() -> int:
        return int(np.clip(int(clip_end_slider.value), 1, n_frames))

    def _last_clip_frame() -> int:
        return max(_clip_start(), _clip_end() - 1)

    def _clamp_frame_to_clip(frame: float) -> float:
        return float(np.clip(frame, _clip_start(), _last_clip_frame()))

    def _sync_segment_index_bounds() -> None:
        segment_index_in.value = int(np.clip(int(segment_index_in.value), 0, max(0, len(segments) - 1)))

    def _default_clip_file_name() -> str:
        return f"{motion_name}_{_clip_start():04d}_{_clip_end():04d}.npz"

    def _clip_path_from_inputs(output_dir: str | None = None, file_name: str | None = None) -> Path:
        out_dir = Path(output_dir or clip_output_dir)
        name = (file_name or _default_clip_file_name()).strip()
        if not name:
            name = _default_clip_file_name()
        if not name.endswith(".npz"):
            name += ".npz"
        return out_dir / name

    def _selected_segment_index() -> int | None:
        selected_id = selected_segment_id["value"]
        if selected_id:
            for i, segment in enumerate(segments):
                if str(segment.get("segment_id", "")) == selected_id:
                    return i
        return None

    def _load_existing_segments() -> None:
        path = Path(segment_export_path)
        if not path.exists():
            return
        loaded = 0
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                segment = json.loads(line)
                if segment.get("motion_id") != motion_name:
                    continue
                segments.append(segment)
                loaded += 1
        if loaded:
            _sync_segment_index_bounds()
            print(f"[segments loaded] {segment_export_path} motion={motion_name} count={loaded}")

    def _clip_file_metadata(path: Path) -> dict[str, object]:
        meta: dict[str, object] = {"duration_frames": None, "source_start_frame": None, "source_end_frame": None}
        try:
            with np.load(path, allow_pickle=True) as data:
                if "qpos" in data:
                    meta["duration_frames"] = int(np.asarray(data["qpos"]).shape[0])
                elif "joint_pos" in data:
                    meta["duration_frames"] = int(np.asarray(data["joint_pos"]).shape[0])
                if "source_start_frame" in data:
                    meta["source_start_frame"] = int(np.asarray(data["source_start_frame"]).reshape(-1)[0])
                if "source_end_frame" in data:
                    meta["source_end_frame"] = int(np.asarray(data["source_end_frame"]).reshape(-1)[0])
        except Exception:
            return meta
        return meta

    def _clip_items() -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        seen: set[str] = set()
        for index, segment in enumerate(segments):
            clip_path = str(segment.get("clip_npz", "") or "")
            if not clip_path:
                continue
            path = Path(clip_path)
            seen.add(str(path))
            start = int(segment.get("start_frame", 0))
            end = int(segment.get("end_frame", start))
            items.append(
                {
                    "kind": "manifest",
                    "segment_index": index,
                    "segment_id": str(segment.get("segment_id", "")),
                    "clip_npz": str(path),
                    "clip_file_name": path.name,
                    "start_frame": start,
                    "end_frame": end,
                    "duration_frames": max(0, end - start),
                    "exists": path.exists(),
                    "current": str(path) == selected_clip_path["value"],
                }
            )

        out_dir = Path(clip_output_dir)
        if out_dir.exists():
            for path in sorted(out_dir.glob("*.npz")):
                path_text = str(path)
                if path_text in seen:
                    continue
                meta = _clip_file_metadata(path)
                items.append(
                    {
                        "kind": "file",
                        "segment_index": None,
                        "segment_id": "",
                        "clip_npz": path_text,
                        "clip_file_name": path.name,
                        "start_frame": meta["source_start_frame"],
                        "end_frame": meta["source_end_frame"],
                        "duration_frames": meta["duration_frames"],
                        "exists": True,
                        "current": path_text == selected_clip_path["value"],
                    }
                )
        return sorted(items, key=lambda item: str(item["clip_file_name"]))

    def _original_motion_items() -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for path_text in original_motion_paths or []:
            path = Path(path_text)
            items.append(
                {
                    "path": str(path),
                    "name": path.stem,
                    "file_name": path.name,
                    "current": str(path) == str(source_motion_npz),
                }
            )
        return items

    def _set_contact_force_data(
        next_contact_force_data: dict[str, np.ndarray | list[str]] | None,
        next_contact_force_npz: str | None,
    ) -> None:
        nonlocal contact_force
        nonlocal contact_force_mask
        nonlocal contact_force_order
        nonlocal contact_force_positions
        nonlocal contact_force_magnitude
        nonlocal contact_force_max
        nonlocal contact_force_npz
        nonlocal contact_force_npz_data
        nonlocal force_line_handle
        nonlocal force_point_handle

        contact_force_npz = next_contact_force_npz
        contact_force_npz_data = next_contact_force_data
        if next_contact_force_data is None:
            contact_force = None
            contact_force_mask = None
            contact_force_order = None
            contact_force_positions = None
            contact_force_magnitude = None
            contact_force_max = 0.0
            if force_line_handle is not None:
                force_line_handle.visible = False
            if force_point_handle is not None:
                force_point_handle.visible = False
            return

        contact_force = np.asarray(next_contact_force_data["force"], dtype=np.float32)
        contact_force_mask = np.asarray(next_contact_force_data["mask"], dtype=bool)
        contact_force_order = [str(x) for x in next_contact_force_data["order"]]
        raw_positions = next_contact_force_data.get("positions")
        contact_force_positions = None if raw_positions is None else np.asarray(raw_positions, dtype=np.float32)
        contact_force_magnitude = np.linalg.norm(contact_force, axis=-1).astype(np.float32)
        contact_force_max = float(np.max(contact_force_magnitude)) if contact_force_magnitude.size else 0.0
        n_parts = int(contact_force.shape[1])
        colors = np.repeat(_contact_colors(n_parts)[:, None, :], 2, axis=1)
        if force_line_handle is None:
            force_line_handle = server.scene.add_line_segments(
                "/contact_forces/vectors",
                points=np.zeros((n_parts, 2, 3), dtype=np.float32),
                colors=colors,
                line_width=4.0,
                visible=True,
            )
        else:
            force_line_handle.visible = True
            force_line_handle.points = np.zeros((n_parts, 2, 3), dtype=np.float32)
            force_line_handle.colors = colors
        if force_point_handle is None:
            force_point_handle = server.scene.add_point_cloud(
                "/contact_forces/points",
                points=np.zeros((n_parts, 3), dtype=np.float32),
                colors=_contact_colors(n_parts),
                point_size=0.045,
                point_shape="circle",
                visible=True,
            )
        else:
            force_point_handle.visible = True
            force_point_handle.points = np.zeros((n_parts, 3), dtype=np.float32)
            force_point_handle.colors = _contact_colors(n_parts)

    def _switch_original_motion(path_text: str) -> dict[str, object]:
        nonlocal qpos
        nonlocal n_frames
        nonlocal has_object_input
        nonlocal motion_name
        nonlocal segment_export_path
        nonlocal source_motion_npz
        nonlocal motion_npz_data
        nonlocal clip_output_dir
        nonlocal viser_object
        nonlocal object_base_frame

        if load_motion_npz is None:
            raise RuntimeError("Original motion switching is not configured.")
        path = Path(path_text)
        next_qpos, next_fps, _next_format, next_motion_npz_data = load_motion_npz(str(path))
        next_qpos = np.asarray(next_qpos)
        if next_qpos.ndim != 2:
            raise ValueError(f"{path} qpos/joint_pos must be [T,D], got {next_qpos.shape}.")
        if next_qpos.shape[0] == 0:
            raise ValueError(f"{path} is empty.")
        if next_qpos.shape[1] < 7 + robot_dof:
            raise ValueError(f"{path} has {next_qpos.shape[1]} columns, expected at least {7 + robot_dof}.")

        _write_segments()

        qpos = next_qpos
        n_frames = int(qpos.shape[0])
        motion_name = path.stem
        source_motion_npz = str(path)
        motion_npz_data = next_motion_npz_data
        segment_export_path = (
            resolve_segment_export_path(str(path))
            if resolve_segment_export_path is not None
            else str(Path("data/motion_viewer/segments") / f"{path.stem}.segments.jsonl")
        )
        clip_output_dir = (
            resolve_clip_output_dir(str(path))
            if resolve_clip_output_dir is not None
            else str(Path("data/motion_viewer/clips") / path.stem)
        )
        if set_object_for_motion is not None:
            viser_object, object_base_frame = set_object_for_motion(str(path))
        has_object_input = (
            viser_object is not None
            and object_base_frame is not None
            and contains_object_in_qpos
            and qpos.shape[1] >= (7 + robot_dof + 7)
        )

        next_contact_force_npz = resolve_contact_force_npz(str(path)) if resolve_contact_force_npz is not None else None
        next_contact_force_data = None
        if next_contact_force_npz is not None and load_contact_force_npz is not None:
            try:
                next_contact_force_data = load_contact_force_npz(next_contact_force_npz, n_frames)
            except Exception as exc:
                print(f"[contact force load failed] {next_contact_force_npz}: {exc}")
                next_contact_force_npz = None
        _set_contact_force_data(next_contact_force_data, next_contact_force_npz)

        segments.clear()
        selected_segment_id["value"] = ""
        selected_clip_path["value"] = ""
        last_delete_result["value"] = None
        _load_existing_segments()

        updating_programmatically["flag"] = True
        frame_slider.value = 0
        clip_start_slider.value = 0
        clip_end_slider.value = n_frames
        fps_in.value = int(next_fps)
        updating_programmatically["flag"] = False
        nonlocal_f["f"] = 0.0
        playing["flag"] = False
        tick["next"] = time.perf_counter()
        prev["robot_q"] = None
        prev["obj_q"] = None
        _apply_discrete_frame(0)
        print(f"[motion switched] {source_motion_npz} frames={n_frames}")
        return {"motion_npz": source_motion_npz, "motion_name": motion_name, "n_frames": n_frames}

    def _slice_npz_dict(data: dict[str, object], start: int, end: int) -> dict[str, object]:
        out: dict[str, object] = {}
        for key, value in data.items():
            arr = np.asarray(value)
            if arr.shape[:1] == (n_frames,):
                out[key] = arr[start:end]
            else:
                out[key] = arr
        return out

    def _write_clip_npz(segment: dict[str, object], output_dir: str | None = None, file_name: str | None = None) -> Path | None:
        if motion_npz_data is None:
            return None
        start = int(segment["start_frame"])
        end = int(segment["end_frame"])
        path = _clip_path_from_inputs(output_dir, file_name)
        path.parent.mkdir(parents=True, exist_ok=True)

        clip_data = _slice_npz_dict(motion_npz_data, start, end)
        if contact_force_npz_data is not None:
            force_data = {
                key: value
                for key, value in contact_force_npz_data.items()
                if key in {"force", "mask", "order", "positions"}
            }
            mapped = {
                "force": "contact_force_part_w",
                "mask": "contact_force_part_mask",
                "order": "contact_force_part_order",
                "positions": "contact_force_part_position_w",
            }
            for key, out_key in mapped.items():
                if key not in force_data or force_data[key] is None:
                    continue
                value = np.asarray(force_data[key])
                clip_data[out_key] = value[start:end] if value.shape[:1] == (n_frames,) else value

        clip_data["source_motion_npz"] = np.asarray(source_motion_npz)
        clip_data["source_contact_force_npz"] = np.asarray(contact_force_npz or "")
        clip_data["source_start_frame"] = np.asarray(start, dtype=np.int64)
        clip_data["source_end_frame"] = np.asarray(end, dtype=np.int64)
        clip_data["atom_label"] = np.asarray(str(segment["atom_label"]))
        clip_data["segment_id"] = np.asarray(str(segment["segment_id"]))
        np.savez_compressed(path, **clip_data)
        return path

    def _write_segments() -> None:
        path = Path(segment_export_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for segment in segments:
                f.write(json.dumps(segment, ensure_ascii=False) + "\n")
        print(f"[segments exported] {segment_export_path} motion={motion_name} count={len(segments)}")

    def _state_dict() -> dict[str, object]:
        current_frame = int(np.clip(int(frame_slider.value), 0, max(0, n_frames - 1)))
        contact_state: dict[str, object] | None = None
        if contact_force is not None and contact_force_mask is not None and contact_force_magnitude is not None:
            contact_state = {
                "order": contact_force_order or [],
                "max_magnitude": contact_force_max,
                "mask": contact_force_mask.astype(int).tolist(),
                "magnitude": np.round(contact_force_magnitude, 2).tolist(),
                "current": [
                    {
                        "part": str((contact_force_order or [])[i]),
                        "force": np.round(contact_force[current_frame, i], 2).tolist(),
                        "magnitude": float(round(float(contact_force_magnitude[current_frame, i]), 2)),
                        "active": bool(contact_force_mask[current_frame, i]),
                    }
                    for i in range(contact_force.shape[1])
                ],
            }
        return {
            "motion_name": motion_name,
            "n_frames": n_frames,
            "fps": int(fps_in.value),
            "visual_fps_multiplier": int(interp_mult_in.value),
            "current_frame": current_frame,
            "start_frame": _clip_start(),
            "end_frame": _clip_end(),
            "playing": bool(playing["flag"]),
            "loop_clip": bool(loop_clip_cb.value),
            "show_meshes": show_meshes_state["value"],
            "segment_export_path": segment_export_path,
            "clip_output_dir": clip_output_dir,
            "default_clip_file_name": _default_clip_file_name(),
            "selected_segment_id": selected_segment_id["value"],
            "selected_segment_index": _selected_segment_index(),
            "selected_clip_path": selected_clip_path["value"],
            "segments": segments,
            "clip_items": _clip_items(),
            "original_motion_items": _original_motion_items(),
            "object": get_object_state() if get_object_state is not None else None,
            "contact_force": contact_state,
            "last_delete_result": last_delete_result["value"],
        }

    def _set_settings(body: dict[str, object]) -> None:
        if "fps" in body:
            fps_in.value = int(np.clip(int(body["fps"]), 1, 240))
        if "visual_fps_multiplier" in body:
            interp_mult_in.value = int(np.clip(int(body["visual_fps_multiplier"]), 1, 8))
        if "loop_clip" in body:
            loop_clip_cb.value = bool(body["loop_clip"])
        if "show_meshes" in body and show_meshes_state["value"] is not None:
            show_meshes_state["value"] = bool(body["show_meshes"])
            if set_show_meshes is not None:
                set_show_meshes(show_meshes_state["value"])
        tick["next"] = time.perf_counter()

    def _set_current_frame(frame: int, stop_playback: bool = True) -> None:
        frame = int(_clamp_frame_to_clip(frame))
        updating_programmatically["flag"] = True
        frame_slider.value = frame
        updating_programmatically["flag"] = False
        nonlocal_f["f"] = float(frame)
        if stop_playback:
            playing["flag"] = False
        tick["next"] = time.perf_counter()
        prev["robot_q"] = None
        prev["obj_q"] = None
        _apply_discrete_frame(frame)

    def _set_clip_range(start: int | None = None, end: int | None = None) -> None:
        next_start = _clip_start() if start is None else int(start)
        next_end = _clip_end() if end is None else int(end)
        next_start = int(np.clip(next_start, 0, max(0, n_frames - 1)))
        next_end = int(np.clip(next_end, 1, n_frames))
        if next_end <= next_start:
            next_end = min(n_frames, next_start + 1)
            if next_end <= next_start:
                next_start = max(0, next_end - 1)
        updating_programmatically["flag"] = True
        clip_start_slider.value = next_start
        clip_end_slider.value = next_end
        frame_slider.value = int(np.clip(int(frame_slider.value), next_start, next_end - 1))
        updating_programmatically["flag"] = False
        nonlocal_f["f"] = float(frame_slider.value)
        playing["flag"] = False
        tick["next"] = time.perf_counter()
        prev["robot_q"] = None
        prev["obj_q"] = None

    def _save_current_segment(output_dir: str | None = None, file_name: str | None = None) -> dict[str, object] | None:
        start = _clip_start()
        end = _clip_end()
        if end <= start:
            return None
        selected_index = _selected_segment_index()
        clip_path = _clip_path_from_inputs(output_dir, file_name)
        segment = {
            "motion_id": motion_name,
            "segment_id": (
                str(segments[selected_index]["segment_id"])
                if selected_index is not None
                else f"{motion_name}_{len(segments):04d}"
            ),
            "start_frame": start,
            "end_frame": end,
            "atom_label": "",
            "clip_npz": str(clip_path),
            "clip_output_dir": str(clip_path.parent),
            "clip_file_name": clip_path.name,
        }
        if selected_index is None:
            segments.append(segment)
            selected_index = len(segments) - 1
        else:
            segments[selected_index] = segment
        selected_segment_id["value"] = str(segment["segment_id"])
        _sync_segment_index_bounds()
        segment_index_in.value = selected_index
        print(
            f"[segment saved] {segment['segment_id']} start={start} end={end} "
            f"label={segment['atom_label']} clip={clip_path} total={len(segments)}"
        )
        written_clip_path = _write_clip_npz(segment, str(clip_path.parent), clip_path.name)
        if written_clip_path is not None:
            segment["clip_npz"] = str(written_clip_path)
            selected_clip_path["value"] = str(written_clip_path)
        _write_segments()
        return segment

    def _delete_segment(index: int, delete_clip_file: bool = False) -> dict[str, object] | None:
        if not segments:
            return None
        index = int(np.clip(index, 0, len(segments) - 1))
        removed = segments.pop(index)
        clip_path_text = str(removed.get("clip_npz", "") or "")
        removed["clip_file_deleted"] = False
        removed["clip_file_missing"] = False
        removed["clip_file_delete_error"] = ""
        if delete_clip_file:
            if clip_path_text:
                clip_path = Path(clip_path_text)
                try:
                    if clip_path.exists():
                        if clip_path.is_file():
                            clip_path.unlink()
                            removed["clip_file_deleted"] = True
                        else:
                            removed["clip_file_delete_error"] = "clip path is not a file"
                    else:
                        removed["clip_file_missing"] = True
                except OSError as exc:
                    removed["clip_file_delete_error"] = str(exc)
            else:
                removed["clip_file_missing"] = True
        if clip_path_text and selected_clip_path["value"] == clip_path_text:
            selected_clip_path["value"] = ""
        _sync_segment_index_bounds()
        if segments:
            next_index = int(np.clip(index, 0, len(segments) - 1))
            segment_index_in.value = next_index
            selected_segment_id["value"] = str(segments[next_index]["segment_id"])
        else:
            selected_segment_id["value"] = ""
        last_delete_result["value"] = removed
        print(
            f"[segment deleted] {removed['segment_id']} remaining={len(segments)} "
            f"clip_deleted={removed['clip_file_deleted']} clip_missing={removed['clip_file_missing']}"
        )
        _write_segments()
        return removed

    def _delete_clip_file_only(path_text: str) -> dict[str, object]:
        path = Path(path_text)
        result: dict[str, object] = {
            "segment_id": "",
            "clip_npz": str(path),
            "clip_file_deleted": False,
            "clip_file_missing": False,
            "clip_file_delete_error": "",
        }
        try:
            if path.exists():
                if path.is_file():
                    path.unlink()
                    result["clip_file_deleted"] = True
                else:
                    result["clip_file_delete_error"] = "clip path is not a file"
            else:
                result["clip_file_missing"] = True
        except OSError as exc:
            result["clip_file_delete_error"] = str(exc)
        if selected_clip_path["value"] == str(path):
            selected_clip_path["value"] = ""
        last_delete_result["value"] = result
        print(
            f"[clip file deleted] path={path} deleted={result['clip_file_deleted']} "
            f"missing={result['clip_file_missing']}"
        )
        return result

    def _select_clip_item(path_text: str, segment_index: int | None = None) -> dict[str, object] | None:
        path = Path(path_text)
        start: int | None = None
        end: int | None = None
        if segment_index is not None and 0 <= segment_index < len(segments):
            segment = segments[segment_index]
            start = int(segment.get("start_frame", 0))
            end = int(segment.get("end_frame", start + 1))
            selected_segment_id["value"] = str(segment.get("segment_id", ""))
            segment_index_in.value = int(segment_index)
        else:
            meta = _clip_file_metadata(path)
            if meta["source_start_frame"] is not None and meta["source_end_frame"] is not None:
                start = int(meta["source_start_frame"])
                end = int(meta["source_end_frame"])
            selected_segment_id["value"] = ""

        selected_clip_path["value"] = str(path)
        if start is None or end is None:
            playing["flag"] = False
            return {"clip_npz": str(path), "loaded_range": False}

        start = int(np.clip(start, 0, max(0, n_frames - 1)))
        end = int(np.clip(end, start + 1, n_frames))
        _set_clip_range(start, end)
        _set_current_frame(start)
        return {"clip_npz": str(path), "loaded_range": True, "start_frame": start, "end_frame": end}

    def _load_segment(index: int) -> dict[str, object] | None:
        if not segments:
            return None
        index = int(np.clip(index, 0, len(segments) - 1))
        segment = segments[index]
        segment_index_in.value = index
        selected_segment_id["value"] = str(segment["segment_id"])
        if str(segment.get("atom_label", "")).isdigit():
            atom_label_in.value = int(str(segment["atom_label"]))
        _set_clip_range(int(segment["start_frame"]), int(segment["end_frame"]))
        _set_current_frame(int(segment["start_frame"]))
        return segment

    def _timeline_html() -> str:
        safe_viser_url = json.dumps(viser_url)
        safe_motion_name = json.dumps(motion_name)
        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Motion Cutter - {motion_name}</title>
<style>
  :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #080911; color: #e8ecf7; overflow: hidden; }}
  #viewer {{ width: 100vw; height: calc(100vh - 360px); border: 0; display: block; }}
  #panel {{ height: 360px; border-top: 1px solid #283043; background: #10131d; padding: 14px 18px; display: grid; grid-template-rows: auto 1fr auto; gap: 10px; }}
  #top {{ display: grid; grid-template-columns: minmax(210px, 1fr) auto; gap: 10px 14px; align-items: center; }}
  #title {{ font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: #8ea3c7; }}
  #readout {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #dbe7ff; }}
  #status {{ color: #8ea3c7; font: 12px ui-monospace, monospace; justify-self: end; }}
  #controls {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px; }}
  button {{ background: #182033; color: #dbe7ff; border: 1px solid #34415f; border-radius: 4px; height: 30px; padding: 0 12px; cursor: pointer; }}
  button:hover {{ border-color: #50c8ff; color: white; }}
  button.primary {{ border-color: #4fa6ff; background: #193253; }}
  button.danger {{ border-color: #6b343a; }}
  select, input {{ background: #0c101a; color: #e8ecf7; border: 1px solid #34415f; border-radius: 4px; height: 30px; padding: 0 8px; }}
  input[type="number"] {{ width: 72px; }}
  input[type="checkbox"] {{ width: 16px; height: 16px; vertical-align: -3px; }}
  label {{ color: #c7d2e7; font-size: 12px; white-space: nowrap; }}
  #main {{ display: grid; grid-template-columns: minmax(360px, 1fr) 320px; gap: 16px; min-height: 0; }}
  #timelineWrap {{ min-width: 0; }}
  #timeline {{ position: relative; height: 158px; margin: 0 8px; cursor: pointer; user-select: none; }}
  #rail {{ position: absolute; left: 0; right: 0; top: 42px; height: 10px; background: #2a3044; border-radius: 2px; }}
  #range {{ position: absolute; top: 34px; height: 26px; background: rgba(31, 184, 255, .26); border: 1px solid rgba(72, 210, 255, .65); border-radius: 3px; pointer-events: none; }}
  .seg {{ position: absolute; top: 72px; height: 16px; background: #44d17a; opacity: .72; border-radius: 2px; cursor: pointer; border: 1px solid transparent; }}
  .seg.selected {{ opacity: 1; border-color: #ffffff; box-shadow: 0 0 0 1px rgba(255,255,255,.35); }}
  .forceLaneLabel {{ position: absolute; left: 0; width: 34px; height: 11px; font: 10px ui-monospace, monospace; color: #8ea3c7; transform: translateX(-40px); }}
  .forceCell {{ position: absolute; height: 9px; border-radius: 1px; opacity: .28; }}
  .forceCell.active {{ opacity: .95; }}
  .handle {{ position: absolute; top: 24px; width: 15px; height: 46px; transform: translateX(-50%); border-radius: 3px; cursor: ew-resize; box-shadow: 0 0 0 1px rgba(0,0,0,.55); }}
  #start {{ background: #2dde7d; }}
  #end {{ background: #ff6b69; }}
  #current {{ width: 5px; height: 76px; top: 10px; background: #ffd166; cursor: grab; }}
  .ticklabel {{ position: absolute; top: 0; transform: translateX(-50%); font: 11px ui-monospace, monospace; color: #8ea3c7; }}
  #hint {{ margin: 0 8px; color: #7785a2; font-size: 12px; }}
  #forceReadout {{ margin: 3px 8px 0; color: #c7d2e7; font: 12px ui-monospace, monospace; min-height: 16px; }}
  #side {{ display: grid; grid-template-rows: auto auto minmax(0, 1fr); gap: 10px; min-height: 0; }}
  #settings {{ display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; justify-content: flex-start; }}
  #sideTabs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
  .sideTab {{ height: 28px; padding: 0 8px; }}
  .sideTab.active {{ border-color: #50c8ff; background: #17304b; color: white; }}
  .listBox {{ min-height: 0; overflow: auto; border: 1px solid #283043; background: #0c101a; }}
  #sideList {{ min-height: 0; }}
  .segmentRow {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 7px 9px; border-bottom: 1px solid #20283a; cursor: pointer; font: 12px ui-monospace, monospace; }}
  .segmentRow:hover {{ background: #141b2b; }}
  .segmentRow.selected {{ background: #1b3146; color: white; }}
  .segmentMeta {{ color: #8ea3c7; }}
  #bottom {{ display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }}
  #message {{ color: #8ea3c7; font: 12px ui-monospace, monospace; }}
  #modalBackdrop {{ position: fixed; inset: 0; background: rgba(4, 6, 12, .72); display: none; align-items: center; justify-content: center; z-index: 10; }}
  #modalBackdrop.open {{ display: flex; }}
  #saveDialog {{ width: min(720px, calc(100vw - 48px)); background: #111827; border: 1px solid #34415f; border-radius: 6px; padding: 16px; box-shadow: 0 18px 60px rgba(0,0,0,.45); }}
  #saveDialog h2 {{ margin: 0 0 12px; font-size: 15px; font-weight: 600; color: #e8ecf7; }}
  #saveDialog .form {{ display: grid; gap: 10px; }}
  #saveDialog label {{ display: grid; gap: 5px; white-space: normal; }}
  #saveDialog input {{ width: 100%; }}
  #savePreview {{ color: #8ea3c7; font: 12px ui-monospace, monospace; overflow-wrap: anywhere; }}
  #saveActions {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }}
  @media (max-width: 860px) {{
    #top {{ grid-template-columns: 1fr; }}
    #controls {{ justify-content: flex-start; }}
    #status {{ justify-self: start; }}
    #viewer {{ height: calc(100vh - 460px); }}
    #panel {{ height: 460px; }}
    #main {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<iframe id="viewer" src={safe_viser_url}></iframe>
<div id="panel">
  <div id="top">
    <div id="title">Motion Cutter</div>
    <div id="controls">
      <button id="play" class="primary">Play Clip</button>
      <button id="save" class="primary">Save cut</button>
      <button id="delete" class="danger">Delete cut</button>
      <button id="reset">Reset range</button>
    </div>
    <div id="readout"></div>
    <div id="status"></div>
  </div>
  <div id="main">
    <div id="timelineWrap">
      <div id="timeline">
        <div id="rail"></div>
        <div id="range"></div>
        <div id="start" class="handle" title="start"></div>
        <div id="current" class="handle" title="current"></div>
        <div id="end" class="handle" title="end"></div>
      </div>
      <div id="forceReadout"></div>
      <div id="hint">Drag yellow=current, green=start, red=end. Click a saved cut to edit it. Space=play clip, S=save, Arrow=step, Shift+Arrow=10 frames.</div>
    </div>
    <div id="side">
      <div id="settings">
        <label><input id="loop" type="checkbox"> Loop</label>
        <label id="meshLabel"><input id="showMeshes" type="checkbox"> Meshes</label>
      </div>
      <div id="sideTabs">
        <button id="motionsTab" class="sideTab">Motions</button>
        <button id="clipsTab" class="sideTab">Clips</button>
      </div>
      <div id="sideList" class="listBox"></div>
    </div>
  </div>
  <div id="bottom">
    <div id="message"></div>
  </div>
</div>
<div id="modalBackdrop">
  <div id="saveDialog" role="dialog" aria-modal="true" aria-labelledby="saveTitle">
    <h2 id="saveTitle">Save Clip NPZ</h2>
    <div class="form">
      <label>Clip dir <input id="modalClipDir" type="text"></label>
      <label>File name <input id="modalClipName" type="text"></label>
      <div id="savePreview"></div>
    </div>
    <div id="saveActions">
      <button id="cancelSave">Cancel</button>
      <button id="confirmSave" class="primary">Save NPZ</button>
    </div>
  </div>
</div>
<script>
const motionName = {safe_motion_name};
let state = null;
let drag = null;
let dragPreview = null;
let modalNameTouched = false;
let activeSideTab = 'clips';
const timeline = document.getElementById('timeline');
const readout = document.getElementById('readout');
const status = document.getElementById('status');
const loop = document.getElementById('loop');
const showMeshes = document.getElementById('showMeshes');
const meshLabel = document.getElementById('meshLabel');
const motionsTab = document.getElementById('motionsTab');
const clipsTab = document.getElementById('clipsTab');
const sideList = document.getElementById('sideList');
const message = document.getElementById('message');
const forceReadout = document.getElementById('forceReadout');
const modalBackdrop = document.getElementById('modalBackdrop');
const modalClipDir = document.getElementById('modalClipDir');
const modalClipName = document.getElementById('modalClipName');
const savePreview = document.getElementById('savePreview');
const forceColors = ['#55b4ff', '#ff785f', '#82eb91', '#f5cd50', '#c896ff', '#ff96d2'];

function clamp(x, lo, hi) {{ return Math.max(lo, Math.min(hi, x)); }}
function currentMin() {{ return state.start_frame; }}
function currentMax() {{ return Math.max(state.start_frame, state.end_frame - 1); }}
function frameToX(frame) {{
  const rect = timeline.getBoundingClientRect();
  return (frame / Math.max(1, state.n_frames - 1)) * rect.width;
}}
function xToFrame(clientX) {{
  const rect = timeline.getBoundingClientRect();
  const ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
  return Math.round(ratio * Math.max(0, state.n_frames - 1));
}}
function xToCurrentFrame(clientX) {{ return clamp(xToFrame(clientX), currentMin(), currentMax()); }}
function clipFullPath() {{
  const dir = modalClipDir.value.trim();
  let name = modalClipName.value.trim();
  if (!name.endsWith('.npz')) name += '.npz';
  if (!dir) return name;
  return dir.replace(/\\/$/, '') + '/' + name;
}}
function updateSavePreview() {{
  savePreview.textContent = 'full path: ' + clipFullPath();
}}
function selectedSegment() {{
  if (state.selected_segment_index === null || state.selected_segment_index === undefined) return null;
  return state.segments[state.selected_segment_index] || null;
}}
function selectedClipItem() {{
  if (!state || !state.clip_items) return null;
  return state.clip_items.find(item => item.current) || null;
}}
function renderSideList() {{
  motionsTab.classList.toggle('active', activeSideTab === 'motions');
  clipsTab.classList.toggle('active', activeSideTab === 'clips');
  sideList.innerHTML = '';
  if (activeSideTab === 'motions') {{
    state.original_motion_items.forEach((item) => {{
      const row = document.createElement('div');
      row.className = 'segmentRow' + (item.current ? ' selected' : '');
      row.onclick = () => switchOriginalMotion(item);
      row.innerHTML = `<div>${{item.name}}<div class="segmentMeta">${{item.file_name}}</div></div><div>${{item.current ? 'current' : ''}}</div>`;
      sideList.appendChild(row);
    }});
    if (state.original_motion_items.length === 0) {{
      sideList.innerHTML = '<div class="segmentRow"><div>No original motions</div><div></div></div>';
    }}
    return;
  }}

  state.clip_items.forEach((item) => {{
    const row = document.createElement('div');
    row.className = 'segmentRow' + (item.current ? ' selected' : '');
    row.onclick = () => loadClipItem(item);
    const range = item.start_frame === null
      ? (item.duration_frames === null ? 'file only' : `${{item.duration_frames}}f`)
      : `${{item.start_frame}}-${{item.end_frame}}  ${{item.duration_frames}}f`;
    const status = item.exists ? range : 'missing file';
    row.innerHTML = `<div>${{item.clip_file_name}}<div class="segmentMeta">${{status}}</div></div><div>${{item.current ? 'viewing' : ''}}</div>`;
    sideList.appendChild(row);
  }});
  if (state.clip_items.length === 0) {{
    sideList.innerHTML = '<div class="segmentRow"><div>No clip files</div><div></div></div>';
  }}
}}
function openSaveDialog() {{
  if (!state) return;
  const seg = selectedSegment();
  modalClipDir.value = (seg && seg.clip_output_dir) || state.clip_output_dir || '';
  modalClipName.value = state.default_clip_file_name || '';
  modalNameTouched = false;
  updateSavePreview();
  modalBackdrop.classList.add('open');
  modalClipName.focus();
  modalClipName.select();
}}
function closeSaveDialog() {{
  modalBackdrop.classList.remove('open');
}}
function showMessage(text) {{
  message.dataset.pinned = '1';
  message.textContent = text;
}}
async function api(path, body) {{
  if (body && path !== '/api/state') message.dataset.pinned = '';
  const res = await fetch(path, {{method: body ? 'POST' : 'GET', headers: {{'Content-Type': 'application/json'}}, body: body ? JSON.stringify(body) : undefined}});
  state = await res.json();
  render();
  return state;
}}
async function refresh() {{ await api('/api/state'); }}
function render() {{
  if (!state) return;
  loop.checked = Boolean(state.loop_clip);
  meshLabel.style.display = state.show_meshes === null ? 'none' : '';
  showMeshes.checked = Boolean(state.show_meshes);
  if (modalBackdrop.classList.contains('open') && !modalNameTouched) {{
    modalClipName.value = state.default_clip_file_name || '';
    updateSavePreview();
  }}
  const sx = frameToX(state.start_frame), cx = frameToX(clamp(state.current_frame, currentMin(), currentMax())), ex = frameToX(state.end_frame - 1);
  document.getElementById('start').style.left = sx + 'px';
  document.getElementById('current').style.left = cx + 'px';
  document.getElementById('end').style.left = ex + 'px';
  const range = document.getElementById('range');
  range.style.left = sx + 'px';
  range.style.width = Math.max(1, ex - sx) + 'px';
  for (const el of [...timeline.querySelectorAll('.seg,.ticklabel,.forceCell,.forceLaneLabel')]) el.remove();
  state.clip_items.forEach((item) => {{
    if (item.start_frame === null || item.end_frame === null) return;
    if (Number(item.end_frame) > state.n_frames) return;
    const el = document.createElement('div');
    el.className = 'seg' + (item.current ? ' selected' : '');
    el.style.left = frameToX(item.start_frame) + 'px';
    el.style.width = Math.max(2, frameToX(item.end_frame - 1) - frameToX(item.start_frame)) + 'px';
    el.title = `${{item.clip_file_name}} ${{item.start_frame}}-${{item.end_frame}}`;
    el.onclick = (e) => {{ e.stopPropagation(); loadClipItem(item); }};
    timeline.appendChild(el);
  }});
  renderSideList();
  for (const [f, label] of [[0,'0'], [state.n_frames - 1, String(state.n_frames - 1)]]) {{
    const t = document.createElement('div');
    t.className = 'ticklabel';
    t.style.left = frameToX(f) + 'px';
    t.textContent = label;
    timeline.appendChild(t);
  }}
  if (state.contact_force) {{
    const maxMag = Math.max(1, state.contact_force.max_magnitude || 1);
    state.contact_force.order.forEach((part, partIndex) => {{
      const label = document.createElement('div');
      label.className = 'forceLaneLabel';
      label.style.top = (96 + partIndex * 13) + 'px';
      label.textContent = part;
      timeline.appendChild(label);
      let runStart = null, runMax = 0;
      const flush = (endIndex) => {{
        if (runStart === null) return;
        const cell = document.createElement('div');
        cell.className = 'forceCell active';
        cell.style.left = frameToX(runStart) + 'px';
        cell.style.width = Math.max(1, frameToX(endIndex) - frameToX(runStart)) + 'px';
        cell.style.top = (97 + partIndex * 13) + 'px';
        const alpha = 0.35 + 0.65 * Math.min(1, runMax / maxMag);
        cell.style.background = forceColors[partIndex % forceColors.length];
        cell.style.opacity = String(alpha);
        timeline.appendChild(cell);
        runStart = null;
        runMax = 0;
      }};
      for (let f = 0; f < state.n_frames; f++) {{
        const active = Boolean(state.contact_force.mask[f][partIndex]);
        const mag = Number(state.contact_force.magnitude[f][partIndex] || 0);
        if (active) {{
          if (runStart === null) runStart = f;
          runMax = Math.max(runMax, mag);
        }} else {{
          flush(f);
        }}
      }}
      flush(state.n_frames - 1);
    }});
    forceReadout.textContent = state.contact_force.current.map(c => `${{c.part}}=${{c.magnitude.toFixed(1)}}N${{c.active ? '*' : ''}}`).join('  ');
  }} else {{
    forceReadout.textContent = 'contact force: none';
  }}
  const dur = state.end_frame - state.start_frame;
  const focusText = dragPreview
    ? `${{dragPreview.label}}=${{dragPreview.frame}}  current=${{state.current_frame}}`
    : `current=${{state.current_frame}}`;
  readout.textContent = `${{state.motion_name}}  ${{focusText}}  in=${{state.start_frame}}  out=${{state.end_frame}}  range=[${{state.start_frame}}, ${{state.end_frame}})  duration=${{dur}}f / ${{(dur/state.fps).toFixed(2)}}s`;
  const objectName = state.object && state.object.urdf ? state.object.urdf.split('/').slice(-3).join('/') : '-';
  const objectNode = state.object && state.object.node ? state.object.node : '-';
  status.textContent = `clips=${{state.clip_items.length}} object=${{objectName}} node=${{objectNode}} selected=${{state.selected_clip_path || '-'}}`;
  if (message.dataset.pinned !== '1') message.textContent = `manifest: ${{state.segment_export_path}}`;
  document.getElementById('play').textContent = state.playing ? 'Pause' : 'Play Clip';
  document.getElementById('save').textContent = state.selected_segment_id ? 'Update cut' : 'Save cut';
}}
function targetFromEvent(e) {{
  const id = e.target.id;
  if (id === 'start' || id === 'current' || id === 'end') return id;
  return 'current';
}}
timeline.addEventListener('pointerdown', e => {{
  if (!state) return;
  drag = targetFromEvent(e);
  timeline.setPointerCapture(e.pointerId);
  updateDrag(e);
}});
timeline.addEventListener('pointermove', e => {{ if (drag) updateDrag(e); }});
function finishDrag() {{
  drag = null;
  dragPreview = null;
  render();
}}
timeline.addEventListener('pointerup', finishDrag);
timeline.addEventListener('pointercancel', finishDrag);
async function updateDrag(e) {{
  const f = xToFrame(e.clientX);
  if (drag === 'current') {{
    dragPreview = null;
    await api('/api/frame', {{frame: xToCurrentFrame(e.clientX)}});
  }} else if (drag === 'start') {{
    const start = Math.min(f, state.end_frame - 1);
    dragPreview = {{label: 'in', frame: start}};
    await api('/api/range', {{start, preview_frame: start}});
  }} else if (drag === 'end') {{
    const end = Math.max(f + 1, state.start_frame + 1);
    dragPreview = {{label: 'out', frame: end}};
    await api('/api/range', {{end, preview_frame: end - 1}});
  }}
}}
loop.onchange = () => api('/api/settings', {{loop_clip: loop.checked}});
showMeshes.onchange = () => api('/api/settings', {{show_meshes: showMeshes.checked}});
document.getElementById('play').onclick = () => api('/api/play', {{playing: !state.playing}});
async function saveClipConfirmed() {{
  const s = await api('/api/save', {{
    clip_output_dir: modalClipDir.value,
    clip_file_name: modalNameTouched ? modalClipName.value : state.default_clip_file_name,
  }});
  const seg = s.segments[s.selected_segment_index];
  closeSaveDialog();
  showMessage(seg && seg.clip_npz ? `saved: ${{seg.clip_npz}}` : 'saved manifest');
}}
async function deleteCutConfirmed() {{
  const item = selectedClipItem();
  if (!item) {{
    showMessage('select a clip file first');
    return;
  }}
  const clipPath = item.clip_npz || '(no clip file recorded)';
  const ok = window.confirm(`Delete clip file?\\n\\n${{clipPath}}`);
  if (!ok) return;
  const body = item.segment_index === null || item.segment_index === undefined
    ? {{clip_npz: item.clip_npz}}
    : {{index: item.segment_index, delete_clip_file: true}};
  const s = await api('/api/delete', body);
  const result = s.last_delete_result || {{}};
  if (result.clip_file_delete_error) {{
    showMessage(`deleted clip record, file delete failed: ${{result.clip_file_delete_error}}`);
  }} else if (result.clip_file_deleted) {{
    showMessage(`deleted clip file: ${{result.clip_npz || clipPath}}`);
  }} else if (result.clip_file_missing) {{
    showMessage(`deleted clip record, file already missing: ${{result.clip_npz || clipPath}}`);
  }} else {{
    showMessage('deleted clip record');
  }}
}}
async function loadClipItem(item) {{
  if (!item.exists) {{
    showMessage(`file missing: ${{item.clip_npz}}`);
    return;
  }}
  const s = await api('/api/select_clip', {{clip_npz: item.clip_npz, segment_index: item.segment_index}});
  const selected = s.clip_items.find(nextItem => nextItem.current);
  if (selected && selected.start_frame !== null) {{
    showMessage(`selected: ${{selected.clip_file_name}}`);
  }} else {{
    showMessage(`selected file, no source range metadata: ${{item.clip_npz}}`);
  }}
}}
async function switchOriginalMotion(item) {{
  if (item.current) return;
  await api('/api/switch_motion', {{motion_npz: item.path}});
  showMessage(`motion: ${{item.name}}`);
}}
document.getElementById('save').onclick = openSaveDialog;
document.getElementById('delete').onclick = deleteCutConfirmed;
motionsTab.onclick = () => {{ activeSideTab = 'motions'; renderSideList(); }};
clipsTab.onclick = () => {{ activeSideTab = 'clips'; renderSideList(); }};
document.getElementById('cancelSave').onclick = closeSaveDialog;
document.getElementById('confirmSave').onclick = saveClipConfirmed;
modalClipDir.oninput = updateSavePreview;
modalClipName.oninput = () => {{ modalNameTouched = true; updateSavePreview(); }};
modalBackdrop.addEventListener('click', e => {{ if (e.target === modalBackdrop) closeSaveDialog(); }});
document.getElementById('reset').onclick = () => api('/api/range', {{start: 0, end: state.n_frames, frame: 0}});
window.addEventListener('keydown', e => {{
  if (!state) return;
  if (modalBackdrop.classList.contains('open')) {{
    if (e.code === 'Escape') {{ e.preventDefault(); closeSaveDialog(); }}
    if (e.code === 'Enter') {{ e.preventDefault(); saveClipConfirmed(); }}
    return;
  }}
  if (e.code === 'Space') {{ e.preventDefault(); api('/api/play', {{playing: !state.playing}}); }}
  if (e.code === 'KeyS') openSaveDialog();
  if (e.code === 'ArrowLeft') api('/api/frame', {{frame: state.current_frame - (e.shiftKey ? 10 : 1)}});
  if (e.code === 'ArrowRight') api('/api/frame', {{frame: state.current_frame + (e.shiftKey ? 10 : 1)}});
}});
refresh();
setInterval(refresh, 500);
</script>
</body>
</html>"""

    def _start_timeline_wrapper() -> None:
        class TimelineHandler(BaseHTTPRequestHandler):
            def _send_json(self, payload: dict[str, object]) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _read_json(self) -> dict[str, object]:
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0:
                    return {}
                return json.loads(self.rfile.read(n).decode("utf-8"))

            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/api/state":
                    self._send_json(_state_dict())
                    return
                html = _timeline_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                body = self._read_json()
                if path == "/api/frame":
                    _set_current_frame(int(body.get("frame", frame_slider.value)))
                elif path == "/api/range":
                    _set_clip_range(
                        int(body["start"]) if "start" in body else None,
                        int(body["end"]) if "end" in body else None,
                    )
                    if "frame" in body:
                        _set_current_frame(int(body["frame"]))
                    elif "preview_frame" in body:
                        playing["flag"] = False
                        _apply_discrete_frame(int(body["preview_frame"]))
                elif path == "/api/play":
                    should_play = bool(body.get("playing", not playing["flag"]))
                    playing["flag"] = should_play
                    if should_play:
                        _set_current_frame(_clip_start(), stop_playback=False)
                    tick["next"] = time.perf_counter()
                elif path == "/api/settings":
                    _set_settings(body)
                elif path == "/api/switch_motion":
                    _switch_original_motion(str(body["motion_npz"]))
                elif path == "/api/save":
                    _save_current_segment(
                        str(body["clip_output_dir"]) if "clip_output_dir" in body else None,
                        str(body["clip_file_name"]) if "clip_file_name" in body else None,
                    )
                elif path == "/api/delete":
                    raw_index = body.get("index")
                    if raw_index is not None:
                        _delete_segment(int(raw_index), delete_clip_file=bool(body.get("delete_clip_file", False)))
                    elif "clip_npz" in body:
                        _delete_clip_file_only(str(body["clip_npz"]))
                elif path == "/api/load":
                    _load_segment(int(body.get("index", 0)))
                elif path == "/api/select_clip":
                    segment_index = body.get("segment_index")
                    _select_clip_item(
                        str(body["clip_npz"]),
                        None if segment_index is None else int(segment_index),
                    )
                elif path == "/api/export":
                    _write_segments()
                self._send_json(_state_dict())

            def log_message(self, _format: str, *args: object) -> None:
                return

        httpd = ThreadingHTTPServer(("127.0.0.1", int(timeline_port)), TimelineHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        print(f"[timeline wrapper] http://localhost:{timeline_port}")

    def _normalize_clip(stop_playback: bool = False) -> None:
        start = _clip_start()
        end = _clip_end()
        if end <= start:
            end = min(n_frames, start + 1)
            if end <= start:
                start = max(0, end - 1)
            updating_programmatically["flag"] = True
            clip_start_slider.value = start
            clip_end_slider.value = end
            updating_programmatically["flag"] = False

        frame = int(_clamp_frame_to_clip(float(frame_slider.value)))
        updating_programmatically["flag"] = True
        frame_slider.value = frame
        updating_programmatically["flag"] = False
        nonlocal_f["f"] = float(frame)
        if stop_playback:
            playing["flag"] = False
        tick["next"] = time.perf_counter()

    _load_existing_segments()

    # ---------------- draw ----------------
    def _apply_contact_force_frame(i: int) -> None:
        if contact_force is None or contact_force_mask is None:
            return
        if force_line_handle is None or force_point_handle is None:
            return
        i = int(np.clip(i, 0, n_frames - 1))
        n_parts = int(contact_force.shape[1])
        if contact_force_positions is not None:
            starts = contact_force_positions[i].astype(np.float32)
        else:
            starts = np.repeat(qpos[i, None, 0:3].astype(np.float32), n_parts, axis=0)

        active = contact_force_mask[i].astype(bool)
        vectors = contact_force[i].astype(np.float32) * float(contact_force_scale)
        vectors[~active] = 0.0
        points = np.stack([starts, starts + vectors], axis=1).astype(np.float32)
        colors = np.repeat(_contact_colors(n_parts)[:, None, :], 2, axis=1).copy()
        colors[~active, :, :] = np.asarray([85, 90, 105], dtype=np.uint8)
        force_line_handle.points = points
        force_line_handle.colors = colors
        force_point_handle.points = starts.astype(np.float32)
        force_point_handle.colors = np.where(
            active[:, None],
            _contact_colors(n_parts),
            np.asarray([85, 90, 105], dtype=np.uint8),
        ).astype(np.uint8)

    def _apply_frame_from_q(q: np.ndarray) -> None:
        # joints -> ensure length
        joints = q[7 : 7 + robot_dof]
        if joints.shape[0] != robot_dof:
            joints = (
                joints[:robot_dof] if joints.shape[0] > robot_dof else np.pad(joints, (0, robot_dof - joints.shape[0]))
            )
        viser_robot.update_cfg(joints)

        # robot base (MuJoCo order: pos first, then quat)
        robot_base_frame.position = q[0:3]  # pos (xyz)
        r_q = _quat_continuous(prev["robot_q"], q[3:7])
        prev["robot_q"] = r_q
        robot_base_frame.wxyz = r_q

        # object (optional) (MuJoCo order: pos first, then quat)
        if has_object_input and object_base_frame is not None:
            object_base_frame.position = q[-7:-4]  # obj pos (xyz)
            o_q = _quat_continuous(prev["obj_q"], q[-4:])
            prev["obj_q"] = o_q
            object_base_frame.wxyz = o_q
        elif object_base_frame is not None and viser_object is not None:
            # fallback static pose
            object_base_frame.position = np.zeros(3)
            object_base_frame.wxyz = np.array([1.0, 0.0, 0.0, 0.0])

    def _apply_discrete_frame(i: int) -> None:
        i = int(np.clip(i, 0, n_frames - 1))
        _apply_frame_from_q(qpos[i])
        _apply_contact_force_frame(i)

    # ---------------- controls ----------------
    @play_btn.on_click
    def _(_evt) -> None:
        should_play = not playing["flag"]
        playing["flag"] = should_play
        if should_play:
            _set_current_frame(_clip_start(), stop_playback=False)
        tick["next"] = time.perf_counter()
        prev["robot_q"] = None
        prev["obj_q"] = None
        nonlocal_f["f"] = float(frame_slider.value)

    @fps_in.on_update
    def _(_evt) -> None:
        tick["next"] = time.perf_counter()

    @interp_mult_in.on_update
    def _(_evt) -> None:
        tick["next"] = time.perf_counter()

    @frame_slider.on_update
    def _(_evt) -> None:
        # Only pause if this is a user interaction, not a programmatic update
        if not updating_programmatically["flag"]:
            # Pause when scrubbing so the background loop doesn't overwrite immediately
            playing["flag"] = False
            tick["next"] = time.perf_counter()
            frame_val = int(_clamp_frame_to_clip(float(frame_slider.value)))
            updating_programmatically["flag"] = True
            frame_slider.value = frame_val
            updating_programmatically["flag"] = False
            _apply_discrete_frame(frame_val)
            prev["robot_q"] = None
            prev["obj_q"] = None
            nonlocal_f["f"] = float(frame_val)

    @clip_start_slider.on_update
    def _(_evt) -> None:
        if not updating_programmatically["flag"]:
            _normalize_clip(stop_playback=True)
            _apply_discrete_frame(int(frame_slider.value))
            prev["robot_q"] = None
            prev["obj_q"] = None

    @clip_end_slider.on_update
    def _(_evt) -> None:
        if not updating_programmatically["flag"]:
            _normalize_clip(stop_playback=True)
            _apply_discrete_frame(int(frame_slider.value))
            prev["robot_q"] = None
            prev["obj_q"] = None

    @set_start_btn.on_click
    def _(_evt) -> None:
        frame_val = int(frame_slider.value)
        updating_programmatically["flag"] = True
        clip_start_slider.value = min(frame_val, max(0, _clip_end() - 1))
        updating_programmatically["flag"] = False
        _normalize_clip(stop_playback=True)

    @set_end_btn.on_click
    def _(_evt) -> None:
        frame_val = int(frame_slider.value)
        updating_programmatically["flag"] = True
        clip_end_slider.value = max(frame_val + 1, _clip_start() + 1)
        updating_programmatically["flag"] = False
        _normalize_clip(stop_playback=True)

    @reset_clip_btn.on_click
    def _(_evt) -> None:
        updating_programmatically["flag"] = True
        clip_start_slider.value = 0
        clip_end_slider.value = n_frames
        frame_slider.value = 0
        updating_programmatically["flag"] = False
        nonlocal_f["f"] = 0.0
        playing["flag"] = False
        prev["robot_q"] = None
        prev["obj_q"] = None
        _apply_discrete_frame(0)

    @save_segment_btn.on_click
    def _(_evt) -> None:
        _save_current_segment()

    @load_segment_btn.on_click
    def _(_evt) -> None:
        _load_segment(int(segment_index_in.value))

    # ---------------- player loop ----------------
    def _player_loop() -> None:
        if n_frames <= 1:
            return
        while True:
            if playing["flag"]:
                now = time.perf_counter()
                fps_val = max(1, int(fps_in.value))
                mult = max(1, int(interp_mult_in.value))
                dt = 1.0 / (fps_val * mult)

                if now >= tick["next"]:
                    # advance by one visual step inside the selected in/out zone
                    start = _clip_start()
                    end = _clip_end()
                    last = max(start, end - 1)
                    f = nonlocal_f["f"] + 1.0 / mult
                    if bool(loop_clip_cb.value):
                        if f > float(last):
                            f = float(start)
                    else:
                        if f > float(last):
                            f = float(last)
                            playing["flag"] = False
                    nonlocal_f["f"] = f

                    k0 = int(np.floor(f))
                    if bool(loop_clip_cb.value) and k0 >= last:
                        k1 = start
                    else:
                        k1 = min(k0 + 1, last)
                    u = float(f - k0)

                    q_interp = _interp_frame(qpos, k0, k1, u)
                    _apply_frame_from_q(q_interp)
                    _apply_contact_force_frame(k0)

                    # Update slider to show current frame number in real-time
                    # Use flag to prevent callback from pausing playback
                    updating_programmatically["flag"] = True
                    frame_slider.value = k0
                    updating_programmatically["flag"] = False

                    tick["next"] = now + dt
                else:
                    time.sleep(min(0.002, max(0.0, tick["next"] - now)))
            else:
                time.sleep(0.02)

    threading.Thread(target=_player_loop, daemon=True).start()

    # initial draw
    _apply_discrete_frame(0)

    if timeline_wrapper:
        _start_timeline_wrapper()

    # keep consistent with your previous return convention
    return [frame_slider], [0.0]
