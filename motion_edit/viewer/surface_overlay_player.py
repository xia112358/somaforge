from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.paths import LAYERS_ROOT
from motion_edit.workbench import move_surface_editor_anchor, read_surface_editor_session, save_surface_editor_session
from motion_edit.workbench.surface_editor_session import SurfaceEditorSession


STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "bound": (80, 180, 255),
    "selected": (255, 220, 90),
    "edited": (130, 235, 145),
    "clamped": (255, 170, 70),
    "suspicious": (255, 120, 95),
    "failed": (255, 80, 80),
    "unbound": (180, 180, 180),
    "surface": (120, 150, 170),
}


@dataclass
class SurfaceOverlayEditorState:
    session_path: Path
    session: SurfaceEditorSession
    overlay_path: Path
    request_path: Path
    selected_anchor_id: str | None = None
    last_error: str | None = None
    last_message: str | None = None
    applied_edit_count: int = 0
    render_generation: int = 0


def load_editor_state(session_path: str | Path) -> SurfaceOverlayEditorState:
    path = Path(session_path).expanduser()
    session = read_surface_editor_session(path)
    return SurfaceOverlayEditorState(
        session_path=path,
        session=session,
        overlay_path=session.overlay_path,
        request_path=session.request_path,
    )


def load_surface_overlay(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def surface_quad_corners(obj: dict[str, Any]) -> list[list[float]]:
    if "corners" in obj and obj["corners"]:
        return [[float(v) for v in corner] for corner in obj["corners"]]
    origin = np.asarray(obj["origin"], dtype=float)
    tangent_u = np.asarray(obj["tangent_u"], dtype=float)
    tangent_v = np.asarray(obj["tangent_v"], dtype=float)
    bounds = obj.get("bounds") or {}
    u0, u1 = [float(v) for v in bounds.get("u", [0.0, 0.0])]
    v0, v1 = [float(v) for v in bounds.get("v", [0.0, 0.0])]
    return [
        (origin + tangent_u * u0 + tangent_v * v0).tolist(),
        (origin + tangent_u * u1 + tangent_v * v0).tolist(),
        (origin + tangent_u * u1 + tangent_v * v1).tolist(),
        (origin + tangent_u * u0 + tangent_v * v1).tolist(),
    ]


def overlay_anchor_items(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    return [obj for obj in overlay.get("objects", []) if obj.get("type") == "anchor_point"]


def append_move_request(
    request_path: str | Path,
    *,
    anchor_id: str,
    tangent_delta: list[float],
    mode: str,
    source: str = "viser_ui",
) -> dict[str, Any]:
    path = Path(request_path).expanduser()
    existing = 0
    if path.exists():
        existing = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    request = {
        "kind": "move_anchor_request",
        "request_id": f"viser_surface_request_{existing:06d}",
        "anchor_id": anchor_id,
        "tangent_delta": [float(tangent_delta[0]), float(tangent_delta[1])],
        "mode": mode,
        "source": source,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(request, sort_keys=True) + "\n")
    return request


def apply_direct_anchor_move(
    state: SurfaceOverlayEditorState,
    *,
    anchor_id: str,
    tangent_delta: list[float],
    mode: str = "reject",
) -> dict[str, Any]:
    moved_graph, edit = move_surface_editor_anchor(
        state.session,
        anchor_id=anchor_id,
        tangent_delta=tangent_delta,
        mode=mode,
    )
    state.selected_anchor_id = anchor_id
    state.applied_edit_count += 1
    state.last_error = None
    state.last_message = f"moved {anchor_id} delta={edit.delta_world}"
    return {
        "motion_id": moved_graph.motion_id,
        "anchor_id": anchor_id,
        "edit_id": edit.edit_id,
        "delta_world": edit.delta_world,
        "tangent_delta": edit.tangent_delta,
        "pending_edits_path": str(state.session.pending_edits_path),
        "overlay_path": str(state.overlay_path),
    }


def save_editor_state(state: SurfaceOverlayEditorState, *, layers_root: Path = LAYERS_ROOT) -> Path | None:
    out = save_surface_editor_session(state.session, layers_root=layers_root)
    state.last_error = None
    state.last_message = f"saved output_contact_layer={out}"
    return out


def _safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in text)


def _color(status: str | None) -> tuple[int, int, int]:
    return STATUS_COLORS.get(str(status or ""), (80, 180, 255))


def _remove_handles(handles: list[Any]) -> None:
    for handle in handles:
        remove = getattr(handle, "remove", None)
        if callable(remove):
            remove()


def _render_overlay(server: Any, overlay: dict[str, Any], *, namespace: str = "/surface_editor") -> list[Any]:
    handles: list[Any] = []
    line_points: list[list[list[float]]] = []
    line_colors: list[list[tuple[int, int, int]]] = []
    anchor_points: list[list[float]] = []
    anchor_colors: list[tuple[int, int, int]] = []

    for obj in overlay.get("objects", []):
        obj_type = obj.get("type")
        status = str(obj.get("status", "bound"))
        color = _color(status)
        if obj_type == "surface_quad":
            corners = surface_quad_corners(obj)
            edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
            for a, b in edges:
                line_points.append([corners[a], corners[b]])
                line_colors.append([color, color])
            if hasattr(server.scene, "add_mesh_simple"):
                name = f"{namespace}/surfaces/{_safe_name(str(obj.get('surface_id', 'surface')))}"
                vertices = np.asarray(corners, dtype=np.float32)
                faces = np.asarray([[0, 1, 2], [0, 2, 3]], dtype=np.uint32)
                try:
                    handle = server.scene.add_mesh_simple(name, vertices, faces, color=tuple(c / 255.0 for c in color), opacity=0.22)
                    handles.append(handle)
                except TypeError:
                    pass
        elif obj_type == "normal_axis":
            line_points.append([obj["from"], obj["to"]])
            line_colors.append([color, color])
        elif obj_type == "projection_line":
            line_points.append([obj["from"], obj["to"]])
            line_colors.append([color, color])
        elif obj_type == "anchor_point":
            anchor_points.append(obj["position"])
            anchor_colors.append(color)

    if line_points:
        handle = server.scene.add_line_segments(
            f"{namespace}/overlay_lines",
            points=np.asarray(line_points, dtype=np.float32),
            colors=np.asarray(line_colors, dtype=np.uint8),
            line_width=3.0,
            visible=True,
        )
        handles.append(handle)
    if anchor_points:
        handle = server.scene.add_point_cloud(
            f"{namespace}/anchor_points",
            points=np.asarray(anchor_points, dtype=np.float32),
            colors=np.asarray(anchor_colors, dtype=np.uint8),
            point_size=0.06,
            point_shape="circle",
            visible=True,
        )
        handles.append(handle)
    return handles


def _load_motion_points(path: str | Path) -> np.ndarray:
    data = np.load(path, allow_pickle=True)
    if "qpos" in data:
        qpos = np.asarray(data["qpos"])
    elif "joint_pos" in data:
        qpos = np.asarray(data["joint_pos"])
    else:
        return np.zeros((0, 3), dtype=np.float32)
    if qpos.ndim != 2 or qpos.shape[1] < 3:
        return np.zeros((0, 3), dtype=np.float32)
    return np.asarray(qpos[:, :3], dtype=np.float32)


def run_surface_overlay_player(args: argparse.Namespace) -> None:
    try:
        import viser  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit("viser is not installed in this environment; use surface-editor fallback/sync commands") from exc

    state = load_editor_state(args.surface_editor_session)
    overlay = load_surface_overlay(args.surface_binding_overlay)
    server = viser.ViserServer(port=args.viser_port)
    server.gui.configure_theme(control_layout="fixed", control_width="large", dark_mode=True, show_logo=False, show_share_button=False)
    server.scene.add_grid("/grid", width=8.0, height=8.0, position=(0.0, 0.0, 0.0))

    motion_points = _load_motion_points(args.qpos_npz)
    if motion_points.shape[0] > 1:
        server.scene.add_line_segments(
            "/motion/root_path",
            points=np.stack([motion_points[:-1], motion_points[1:]], axis=1),
            colors=np.full((motion_points.shape[0] - 1, 2, 3), 160, dtype=np.uint8),
            line_width=1.5,
            visible=True,
        )
    render_handles = {"value": _render_overlay(server, overlay)}

    def _refresh_overlay() -> dict[str, Any]:
        state.render_generation += 1
        next_overlay = load_surface_overlay(state.overlay_path)
        _remove_handles(render_handles["value"])
        render_handles["value"] = _render_overlay(server, next_overlay, namespace=f"/surface_editor/render_{state.render_generation:06d}")
        return next_overlay

    anchors = overlay_anchor_items(overlay)
    anchor_ids = [str(anchor.get("anchor_id", "")) for anchor in anchors if anchor.get("anchor_id")]
    selected_default = anchor_ids[0] if anchor_ids else ""
    with server.gui.add_folder("Surface Anchor Editor"):
        anchor_id = server.gui.add_text("anchor_id", initial_value=selected_default)
        du = server.gui.add_number("du", initial_value=0.0, step=0.01)
        dv = server.gui.add_number("dv", initial_value=0.0, step=0.01)
        mode = server.gui.add_dropdown("mode", options=("reject", "clamp"), initial_value="reject")
        move_btn = server.gui.add_button("Move anchor" if args.edit_mode == "direct" else "Write move request")
        request_btn = server.gui.add_button("Write request only")
        reload_btn = server.gui.add_button("Reload overlay")
        save_btn = server.gui.add_button("Save edits")
        status_text = server.gui.add_text("status", initial_value="ready")

    @move_btn.on_click
    def _(_) -> None:
        if not str(anchor_id.value).strip():
            print("[surface editor] no anchor_id selected")
            status_text.value = "error: no anchor_id selected"
            return
        if args.edit_mode == "request":
            request = append_move_request(
                args.surface_editor_requests,
                anchor_id=str(anchor_id.value).strip(),
                tangent_delta=[float(du.value), float(dv.value)],
                mode=str(mode.value),
            )
            status_text.value = f"request written: {request['request_id']}"
            print(f"[surface editor] wrote request {request['request_id']} anchor={request['anchor_id']}")
            print(f"[surface editor] apply with: motion-edit surface-editor-sync --session {args.surface_editor_session}")
            return
        try:
            result = apply_direct_anchor_move(
                state,
                anchor_id=str(anchor_id.value).strip(),
                tangent_delta=[float(du.value), float(dv.value)],
                mode=str(mode.value),
            )
            _refresh_overlay()
            status_text.value = f"moved {result['anchor_id']} delta={result['delta_world']}"
            print(f"[surface editor] moved anchor={result['anchor_id']} edit={result['edit_id']}")
        except Exception as exc:
            state.last_error = str(exc)
            status_text.value = f"error: {exc}"
            print(f"[surface editor] move failed anchor={anchor_id.value}: {exc}")

    @request_btn.on_click
    def _(_) -> None:
        if not str(anchor_id.value).strip():
            status_text.value = "error: no anchor_id selected"
            return
        request = append_move_request(
            args.surface_editor_requests,
            anchor_id=str(anchor_id.value).strip(),
            tangent_delta=[float(du.value), float(dv.value)],
            mode=str(mode.value),
        )
        status_text.value = f"request written: {request['request_id']}"
        print(f"[surface editor] wrote request {request['request_id']} anchor={request['anchor_id']}")

    @reload_btn.on_click
    def _(_) -> None:
        next_overlay = _refresh_overlay()
        status_text.value = f"reloaded overlay objects={len(next_overlay.get('objects', []))}"

    @save_btn.on_click
    def _(_) -> None:
        try:
            out = save_editor_state(state)
            status_text.value = f"saved: {out}"
            print(f"[surface editor] saved output_contact_layer={out}")
        except Exception as exc:
            state.last_error = str(exc)
            status_text.value = f"save error: {exc}"
            print(f"[surface editor] save failed: {exc}")

    print(f"[surface editor] overlay={args.surface_binding_overlay}")
    print(f"[surface editor] session={args.surface_editor_session}")
    print(f"[surface editor] requests={args.surface_editor_requests}")
    print(f"[surface editor] edit_mode={args.edit_mode}")
    if anchor_ids:
        print(f"[surface editor] anchors={', '.join(anchor_ids[:20])}{' ...' if len(anchor_ids) > 20 else ''}")
    print("Close this process with Ctrl+C.")
    while True:
        time.sleep(1.0)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Viser surface binding overlay player.")
    parser.add_argument("--qpos-npz", required=True)
    parser.add_argument("--surface-binding-overlay", required=True)
    parser.add_argument("--surface-editor-session", required=True)
    parser.add_argument("--surface-editor-requests", required=True)
    parser.add_argument("--edit-mode", choices=("direct", "request"), default="direct")
    parser.add_argument("--viser-port", type=int, default=None)
    parser.add_argument("--timeline-port", type=int, default=8094)
    parser.add_argument("--fps", type=int, default=50)
    parser.add_argument("--with-terrain", action="store_true")
    return parser


def main() -> None:
    run_surface_overlay_player(build_arg_parser().parse_args())


if __name__ == "__main__":
    main()
