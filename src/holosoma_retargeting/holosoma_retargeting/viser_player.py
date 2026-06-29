#!/usr/bin/env python3
# viser_player.py
from __future__ import annotations

import json
import re
import sys
import time
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh  # type: ignore[import-untyped]
import tyro
import viser  # type: ignore[import-not-found]  # pip install viser
import yourdfpy  # type: ignore[import-untyped]  # pip install yourdfpy
from viser.extras import ViserUrdf  # type: ignore[import-not-found]

src_root = Path(__file__).resolve().parent.parent
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))
from holosoma_retargeting.config_types.viser import ViserConfig  # noqa: E402
from holosoma_retargeting.src.viser_utils import create_motion_control_sliders  # noqa: E402


class StaticUrdfMeshes:
    """Render static URDF visual meshes without depending on a URDF scene graph."""

    def __init__(self, server: viser.ViserServer, urdf_path: str, root_node_name: str):
        self._server = server
        self._urdf_path = Path(urdf_path)
        self._root_node_name = root_node_name.rstrip("/")
        self._meshes: list[viser.SceneNodeHandle] = []
        self._visible = True
        self._load()

    @property
    def show_visual(self) -> bool:
        return self._visible

    @show_visual.setter
    def show_visual(self, visible: bool) -> None:
        self._visible = bool(visible)
        for mesh in self._meshes:
            mesh.visible = self._visible

    def remove(self) -> None:
        for mesh in self._meshes:
            mesh.remove()
        self._meshes.clear()

    def _load(self) -> None:
        tree = ET.parse(self._urdf_path)
        robot = tree.getroot()
        mesh_index = 0
        for link in robot.findall("link"):
            link_name = link.attrib.get("name", f"link_{mesh_index}")
            for visual in link.findall("visual"):
                mesh_el = visual.find("geometry/mesh")
                if mesh_el is None:
                    continue
                filename = mesh_el.attrib.get("filename")
                if not filename:
                    continue

                mesh_path = Path(filename)
                if not mesh_path.is_absolute():
                    mesh_path = self._urdf_path.parent / mesh_path
                mesh = trimesh.load_mesh(mesh_path, force="mesh")
                if isinstance(mesh, trimesh.Scene):
                    mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
                if not isinstance(mesh, trimesh.Trimesh):
                    continue

                scale = _parse_vec3(mesh_el.attrib.get("scale"), default=(1.0, 1.0, 1.0))
                mesh = mesh.copy()
                mesh.apply_scale(scale)

                origin = visual.find("origin")
                if origin is not None:
                    xyz = _parse_vec3(origin.attrib.get("xyz"), default=(0.0, 0.0, 0.0))
                    rpy = _parse_vec3(origin.attrib.get("rpy"), default=(0.0, 0.0, 0.0))
                    mesh.apply_transform(_origin_transform(xyz, rpy))

                color = _visual_rgba(visual)
                mesh_name = f"{self._root_node_name}/visual/{_safe_scene_name(link_name)}_{mesh_index}"
                if color is None:
                    handle = self._server.scene.add_mesh_trimesh(mesh_name, mesh)
                else:
                    handle = self._server.scene.add_mesh_simple(
                        mesh_name,
                        mesh.vertices,
                        mesh.faces,
                        color=tuple(float(x) for x in color[:3]),
                        opacity=float(color[3]),
                    )
                self._meshes.append(handle)
                mesh_index += 1


def _parse_vec3(text: str | None, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if not text:
        return default
    values = [float(x) for x in text.split()]
    if len(values) != 3:
        return default
    return values[0], values[1], values[2]


def _origin_transform(xyz: tuple[float, float, float], rpy: tuple[float, float, float]) -> np.ndarray:
    roll, pitch, yaw = rpy
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    transform = np.eye(4)
    transform[:3, :3] = rz @ ry @ rx
    transform[:3, 3] = np.asarray(xyz, dtype=float)
    return transform


def _visual_rgba(visual: ET.Element) -> tuple[float, float, float, float] | None:
    color = visual.find("material/color")
    if color is None:
        return None
    rgba_text = color.attrib.get("rgba")
    if not rgba_text:
        return None
    values = [float(x) for x in rgba_text.split()]
    if len(values) != 4:
        return None
    return values[0], values[1], values[2], values[3]


def _safe_scene_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in name)


def _is_terrain_urdf(path: str) -> bool:
    object_path = Path(path)
    return "terrain" in object_path.parts and object_path.name.startswith("multi_boxes_z_scale_")


def load_npz(npz_path: str):
    data = np.load(npz_path, allow_pickle=True)
    data_dict = {key: data[key] for key in data.files}
    fps = int(np.asarray(data["fps"]).reshape(-1)[0]) if "fps" in data else 30

    # Legacy viewer format: qpos [T, ?].
    if "qpos" in data:
        return data["qpos"], fps, "qpos", data_dict

    # Holosoma WBT format:
    # joint_pos is [root_xyz, root_quat_wxyz, robot_joint_pos...].
    if "joint_pos" in data:
        return data["joint_pos"], fps, "holosoma_joint_pos", data_dict

    raise KeyError(f"{npz_path} has neither 'qpos' nor Holosoma 'joint_pos'.")


def load_contact_force_npz(npz_path: str, expected_frames: int) -> dict[str, np.ndarray | list[str]]:
    data = np.load(npz_path, allow_pickle=True)
    required = ("contact_force_part_w", "contact_force_part_mask", "contact_force_part_order")
    missing = [key for key in required if key not in data]
    if missing:
        raise KeyError(f"{npz_path} missing contact-force keys: {missing}")

    force = np.asarray(data["contact_force_part_w"], dtype=np.float32)
    mask = np.asarray(data["contact_force_part_mask"], dtype=bool)
    order = [str(x) for x in np.asarray(data["contact_force_part_order"]).reshape(-1)]
    if force.ndim != 3 or force.shape[-1] != 3:
        raise ValueError(f"contact_force_part_w must be [T,P,3], got {force.shape}")
    if mask.shape != force.shape[:2]:
        raise ValueError(f"contact_force_part_mask must be {force.shape[:2]}, got {mask.shape}")
    if force.shape[0] != expected_frames:
        raise ValueError(f"contact force frames={force.shape[0]} does not match motion frames={expected_frames}")

    positions = None
    if "contact_force_part_position_w" in data:
        raw_positions = np.asarray(data["contact_force_part_position_w"], dtype=np.float32)
        if raw_positions.shape != force.shape:
            raise ValueError(
                f"contact_force_part_position_w must be {force.shape}, got {raw_positions.shape}"
            )
        positions = raw_positions
    elif "body_pos_w" in data and "body_names" in data:
        body_pos = np.asarray(data["body_pos_w"], dtype=np.float32)
        body_names = [str(x) for x in np.asarray(data["body_names"]).reshape(-1)]
        part_body_names: dict[str, list[str]] = {}
        if "contact_force_part_body_names_json" in data:
            part_body_names = json.loads(str(np.asarray(data["contact_force_part_body_names_json"]).item()))

        part_positions = []
        for part in order:
            names = part_body_names.get(part, [])
            ids = [body_names.index(name) for name in names if name in body_names]
            if not ids:
                ids = [
                    i
                    for i, name in enumerate(body_names)
                    if (part == "LF" and ("left_ankle" in name or "left_foot" in name))
                    or (part == "RF" and ("right_ankle" in name or "right_foot" in name))
                    or (part == "LH" and ("left_wrist" in name or "left_hand" in name))
                    or (part == "RH" and ("right_wrist" in name or "right_hand" in name))
                ][:1]
            if ids:
                part_positions.append(body_pos[:, ids, :].mean(axis=1))
            else:
                part_positions.append(np.zeros((expected_frames, 3), dtype=np.float32))
        positions = np.stack(part_positions, axis=1).astype(np.float32)

    return {
        "force": force,
        "mask": mask,
        "order": order,
        "positions": positions,
    }


def resolve_contact_force_npz(qpos_npz: str, contact_force_npz: str | None) -> str | None:
    if contact_force_npz:
        return contact_force_npz

    motion_stem = Path(qpos_npz).stem
    search_dir = Path("data/contact_force_demos")
    if not search_dir.exists():
        return None

    candidates = sorted(search_dir.glob(f"{motion_stem}_force_demo*.npz"))
    if not candidates:
        return None
    preferred = [p for p in candidates if "29motion_model16000" in p.name]
    return str((preferred or candidates)[-1])


def resolve_segment_export_path(qpos_npz: str, segment_export_path: str | None) -> str:
    if segment_export_path:
        return segment_export_path
    motion_stem = Path(qpos_npz).stem
    return str(Path("data/motion_viewer/segments") / f"{motion_stem}.segments.jsonl")


def resolve_clip_output_dir(qpos_npz: str, clip_output_dir: str | None) -> str:
    if clip_output_dir:
        return clip_output_dir
    motion_stem = Path(qpos_npz).stem
    return str(Path("data/motion_viewer/clips") / motion_stem)


def resolve_original_motion_paths(qpos_npz: str) -> list[str]:
    motion_dir = Path(qpos_npz).parent
    if not motion_dir.exists():
        return [qpos_npz]
    pattern = "*_original.npz" if Path(qpos_npz).stem.endswith("_original") else "*.npz"
    paths = sorted(motion_dir.glob(pattern))
    return [str(path) for path in paths] or [qpos_npz]


def resolve_object_urdf(qpos_npz: str, object_urdf: str | None) -> str | None:
    stem = Path(qpos_npz).stem
    parts = stem.split("_")
    is_climb_motion = len(parts) >= 2 and parts[0] == "climb"
    is_mocap_climb_motion = len(parts) >= 4 and parts[:3] == ["mocap", "climb", "seq"]

    if object_urdf:
        object_path = Path(object_urdf)
        is_terrain_override = "terrain" in object_path.parts and object_path.name.startswith("multi_boxes_z_scale_")
        is_mocap_override = (
            "demo_data" in object_path.parts
            and "climb" in object_path.parts
            and re.fullmatch(r"mocap_climb_seq_\d+", object_path.parent.name) is not None
        )
        if not ((is_terrain_override and is_climb_motion) or (is_mocap_override and is_mocap_climb_motion)):
            return object_urdf

    if is_mocap_climb_motion:
        terrain_path = (
            Path("demo_data/climb")
            / f"mocap_climb_seq_{parts[3]}"
            / "multi_boxes_scaled_0.74_0.74_0.74.urdf"
        )
        return str(terrain_path) if terrain_path.exists() else None

    if not is_climb_motion:
        return None
    terrain_id = f"climb_{parts[1]}"

    z_scale = "1.0"
    if "z" in parts and "scale" in parts:
        for i in range(len(parts) - 2):
            if parts[i] == "z" and parts[i + 1] == "scale":
                z_scale = parts[i + 2]
                break

    terrain_path = Path("OmniRetarget_Dataset/models/terrain") / terrain_id / f"multi_boxes_z_scale_{z_scale}.urdf"
    return str(terrain_path) if terrain_path.exists() else None


def make_player(
    config: ViserConfig,
    qpos: np.ndarray,
    motion_npz_data: dict[str, np.ndarray],
    fps: int | None = None,
    motion_format: str = "qpos",
):
    """
    qpos layout (MuJoCo order):
      [0:3]   robot base position (xyz)
      [3:7]   robot base quat (wxyz)
      [7:7+R] robot joint positions (R = actuated dof)
      [end-7:end-4] (optional) object position (xyz)
      [end-4:end]   (optional) object quat (wxyz)

    We'll infer R from the robot URDF's actuated joints in ViserUrdf.
    """
    server = viser.ViserServer()
    if config.timeline_wrapper:
        server.gui.configure_theme(
            control_layout="collapsible",
            control_width="small",
            dark_mode=True,
            show_logo=False,
            show_share_button=False,
        )
    else:
        server.gui.configure_theme(control_layout="fixed", control_width="large")

    # Root frames
    robot_root = server.scene.add_frame("/robot", show_axes=False)

    # URDFs (using yourdfpy so meshes show up)
    robot_urdf_y = yourdfpy.URDF.load(config.robot_urdf, load_meshes=True, build_scene_graph=True)
    vr = ViserUrdf(server, urdf_or_path=robot_urdf_y, root_node_name="/robot")

    current_object = {
        "viser_object": None,
        "root": None,
        "urdf": "",
        "node": "",
    }
    object_generation = {"value": 0}
    show_meshes_value = {"value": bool(config.show_meshes)}

    def _remove_current_object() -> None:
        if current_object["viser_object"] is not None:
            current_object["viser_object"].remove()
        if current_object["root"] is not None:
            current_object["root"].remove()
        current_object["viser_object"] = None
        current_object["root"] = None
        current_object["urdf"] = ""
        current_object["node"] = ""

    def _set_object_for_motion(qpos_npz: str) -> tuple[ViserUrdf | None, viser.FrameHandle | None]:
        next_object_urdf = resolve_object_urdf(qpos_npz, config.object_urdf)
        _remove_current_object()
        if not next_object_urdf:
            return None, None

        object_generation["value"] += 1
        node_name = f"/objects/{Path(qpos_npz).stem}_{object_generation['value']}"
        root = server.scene.add_frame(node_name, show_axes=False)
        if _is_terrain_urdf(next_object_urdf):
            viser_object = StaticUrdfMeshes(server, next_object_urdf, root_node_name=node_name)
        else:
            object_urdf_y = yourdfpy.URDF.load(next_object_urdf, load_meshes=True, build_scene_graph=True)
            viser_object = ViserUrdf(server, urdf_or_path=object_urdf_y, root_node_name=node_name)
        viser_object.show_visual = bool(show_meshes_value["value"])
        root.visible = True
        root.position = (0.0, 0.0, 0.0)
        root.wxyz = (1.0, 0.0, 0.0, 0.0)
        current_object["viser_object"] = viser_object
        current_object["root"] = root
        current_object["urdf"] = next_object_urdf
        current_object["node"] = node_name
        print(f"[terrain switched] {Path(qpos_npz).name} -> {next_object_urdf} node={node_name}")
        return viser_object, root

    vo, object_root = _set_object_for_motion(config.qpos_npz)

    # A tiny grid
    server.scene.add_grid("/grid", width=config.grid_width, height=config.grid_height, position=(0.0, 0.0, 0.0))

    # Figure robot DOF from actuated limits in ViserUrdf
    joint_limits = vr.get_actuated_joint_limits()
    robot_dof = len(joint_limits)
    expected_min_cols = 7 + robot_dof
    if qpos.shape[1] < expected_min_cols:
        raise ValueError(
            f"Motion has {qpos.shape[1]} qpos columns, but robot '{config.robot_urdf}' needs at least "
            f"{expected_min_cols} columns (= 7 root pose + {robot_dof} actuated joints)."
        )

    # Use fps from config if not provided, otherwise use the one from npz file
    actual_fps = fps if fps is not None else config.fps
    contact_force_npz = resolve_contact_force_npz(config.qpos_npz, config.contact_force_npz)
    contact_force_data = load_contact_force_npz(contact_force_npz, int(qpos.shape[0])) if contact_force_npz is not None else None
    segment_export_path = resolve_segment_export_path(config.qpos_npz, config.segment_export_path)
    clip_output_dir = resolve_clip_output_dir(config.qpos_npz, config.clip_output_dir)
    original_motion_paths = resolve_original_motion_paths(config.qpos_npz)

    # Set initial mesh visibility
    vr.show_visual = config.show_meshes
    if vo is not None:
        vo.show_visual = config.show_meshes

    # ---------- Additional GUI controls (mesh visibility) ----------
    if config.timeline_wrapper:
        class _ValueBox:
            def __init__(self, value):
                self.value = value

            def on_update(self, fn):
                return fn

        show_meshes_cb = _ValueBox(config.show_meshes)
    else:
        with server.gui.add_folder("Display"):
            show_meshes_cb = server.gui.add_checkbox("Show meshes", initial_value=config.show_meshes)

    @show_meshes_cb.on_update
    def _(_):
        show_meshes_value["value"] = bool(show_meshes_cb.value)
        vr.show_visual = bool(show_meshes_cb.value)
        if current_object["viser_object"] is not None:
            current_object["viser_object"].show_visual = bool(show_meshes_cb.value)

    def _set_show_meshes(value: bool) -> None:
        show_meshes_value["value"] = bool(value)
        show_meshes_cb.value = bool(value)
        vr.show_visual = bool(value)
        if current_object["viser_object"] is not None:
            current_object["viser_object"].show_visual = bool(value)

    # ---------- Use reusable motion control sliders from viser_utils ----------
    create_motion_control_sliders(
        server=server,
        viser_robot=vr,
        robot_base_frame=robot_root,
        motion_sequence=qpos,
        robot_dof=robot_dof,
        viser_object=vo,
        object_base_frame=object_root if vo is not None else None,
        contains_object_in_qpos=config.assume_object_in_qpos,
        initial_fps=actual_fps,
        initial_interp_mult=config.visual_fps_multiplier,
        loop=config.loop,
        motion_name=Path(config.qpos_npz).stem,
        segment_export_path=segment_export_path,
        source_motion_npz=config.qpos_npz,
        motion_npz_data=motion_npz_data,
        clip_output_dir=clip_output_dir,
        timeline_wrapper=config.timeline_wrapper,
        timeline_port=config.timeline_port,
        viser_url=f"http://localhost:{server.get_port()}",
        show_meshes=config.show_meshes,
        set_show_meshes=_set_show_meshes,
        contact_force=contact_force_data["force"] if contact_force_data is not None else None,
        contact_force_mask=contact_force_data["mask"] if contact_force_data is not None else None,
        contact_force_order=contact_force_data["order"] if contact_force_data is not None else None,
        contact_force_positions=contact_force_data["positions"] if contact_force_data is not None else None,
        contact_force_npz=contact_force_npz,
        contact_force_npz_data=contact_force_data,
        contact_force_scale=config.contact_force_scale,
        original_motion_paths=original_motion_paths,
        load_motion_npz=load_npz,
        resolve_segment_export_path=lambda path: resolve_segment_export_path(path, None),
        resolve_clip_output_dir=lambda path: resolve_clip_output_dir(path, None),
        resolve_contact_force_npz=lambda path: resolve_contact_force_npz(path, None),
        load_contact_force_npz=load_contact_force_npz,
        set_object_for_motion=_set_object_for_motion,
        get_object_state=lambda: {"urdf": current_object["urdf"], "node": current_object["node"]},
    )
    n_frames = int(qpos.shape[0])
    print(
        f"[viser_player] Loaded {n_frames} frames | robot_dof={robot_dof} | "
        f"format={motion_format} | object={'animated' if (vo is not None and config.assume_object_in_qpos) else ('static' if vo is not None else 'no')}"
    )
    print(f"[viser_player] Object URDF: {current_object['urdf'] or 'none'}")
    print(f"[viser_player] Segment export path: {segment_export_path}")
    print(f"[viser_player] Clip output dir: {clip_output_dir}")
    if contact_force_data is not None:
        print(
            f"[viser_player] Contact force: {contact_force_npz} "
            f"parts={contact_force_data['order']}"
        )
    else:
        print("[viser_player] Contact force: none")
    if config.timeline_wrapper:
        wrapper_url = f"http://localhost:{config.timeline_port}"
        print("")
        print("=" * 72)
        print("Open Motion Cutter:")
        print(wrapper_url)
        print("=" * 72)
        print("")
        if config.open_browser:
            opened = webbrowser.open(wrapper_url, new=2)
            print(f"[viser_player] open_browser={opened} url={wrapper_url}")
        print("Open the timeline wrapper URL above. Close the process (Ctrl+C) to exit.")
    else:
        print("Open the Viser viewer URL printed above. Close the process (Ctrl+C) to exit.")
    return server


def main(cfg: ViserConfig) -> None:
    """Main function for viser player."""
    qpos, fps, motion_format, motion_npz_data = load_npz(cfg.qpos_npz)
    make_player(
        config=cfg,
        qpos=qpos,
        motion_npz_data=motion_npz_data,
        fps=fps,
        motion_format=motion_format,
    )

    # keep process alive
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    cfg = tyro.cli(ViserConfig)
    main(cfg)
