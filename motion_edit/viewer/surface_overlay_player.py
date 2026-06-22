from __future__ import annotations

import argparse
import copy
import json
import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.paths import LAYERS_ROOT
from motion_edit.workbench import (
    move_surface_editor_anchor,
    read_pending_surface_edits,
    read_surface_editor_graph,
    read_surface_editor_session,
    save_surface_editor_session,
    write_pending_surface_edits,
    write_surface_editor_graph,
)
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

STATUS_COLOR_OVERRIDES = {"selected", "edited", "clamped", "suspicious", "failed"}

BODY_COLORS: dict[str, tuple[int, int, int]] = {
    "lf": (60, 140, 255),
    "left_foot": (60, 140, 255),
    "rf": (255, 120, 65),
    "right_foot": (255, 120, 65),
    "lh": (80, 210, 130),
    "left_hand": (80, 210, 130),
    "rh": (210, 110, 255),
    "right_hand": (210, 110, 255),
    "lk": (255, 205, 70),
    "left_knee": (255, 205, 70),
    "rk": (90, 220, 220),
    "right_knee": (90, 220, 220),
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


@dataclass
class SurfaceEditorController:
    server: Any
    state: SurfaceOverlayEditorState
    render_handles: list[Any] = field(default_factory=list)
    selected_anchor_id: str | None = None
    undo_stack: list[tuple[ContactGraph, list[ContactAnchorEditRecord]]] = field(default_factory=list)
    redo_stack: list[tuple[ContactGraph, list[ContactAnchorEditRecord]]] = field(default_factory=list)
    last_overlay: dict[str, Any] = field(default_factory=dict)
    original_graph: ContactGraph | None = None
    on_change: Any = None
    drag_mode_getter: Any = None
    edit_mode: str = "direct"

    @classmethod
    def create(cls, server: Any, state: SurfaceOverlayEditorState) -> "SurfaceEditorController":
        graph = read_surface_editor_graph(state.session)
        overlay = load_surface_overlay(state.overlay_path)
        controller = cls(server=server, state=state, last_overlay=overlay, original_graph=copy.deepcopy(graph))
        controller.selected_anchor_id = controller.default_anchor_id()
        controller.state.selected_anchor_id = controller.selected_anchor_id
        return controller

    def graph(self) -> ContactGraph:
        return read_surface_editor_graph(self.state.session)

    def pending_edits(self) -> list[ContactAnchorEditRecord]:
        return read_pending_surface_edits(self.state.session)

    def _snapshot(self) -> tuple[ContactGraph, list[ContactAnchorEditRecord]]:
        return copy.deepcopy(self.graph()), copy.deepcopy(self.pending_edits())

    def _restore(self, snapshot: tuple[ContactGraph, list[ContactAnchorEditRecord]]) -> None:
        graph, edits = snapshot
        write_surface_editor_graph(self.state.session, graph)
        write_pending_surface_edits(self.state.session, edits)
        self.reload_overlay()

    def anchors(self) -> list[dict[str, Any]]:
        overlay = load_surface_overlay(self.state.overlay_path)
        return overlay_anchor_items(overlay)

    def _anchor_obj(self, anchor_id: str | None = None) -> dict[str, Any] | None:
        target = anchor_id or self.selected_anchor_id
        if not target:
            return None
        for anchor in self.anchors():
            if anchor.get("anchor_id") == target:
                return anchor
        return None

    def _anchor_record(self, anchor_id: str | None = None) -> ContactAnchorRecord | None:
        target = anchor_id or self.selected_anchor_id
        if not target:
            return None
        for anchor in self.graph().anchors:
            if anchor.anchor_id == target:
                return anchor
        return None

    def _original_anchor_record(self, anchor_id: str | None = None) -> ContactAnchorRecord | None:
        target = anchor_id or self.selected_anchor_id
        if not target or self.original_graph is None:
            return None
        for anchor in self.original_graph.anchors:
            if anchor.anchor_id == target:
                return anchor
        return None

    def default_anchor_id(self) -> str | None:
        anchors = self.anchors()
        for status in ("bound", "edited", "clamped", "suspicious"):
            for anchor in anchors:
                if anchor.get("status") == status:
                    return str(anchor.get("anchor_id"))
        return str(anchors[0].get("anchor_id")) if anchors else None

    def filter_anchors(self, *, text: str = "", status: str = "all", surface: str = "") -> list[dict[str, Any]]:
        text = text.strip().lower()
        surface = surface.strip().lower()
        out = []
        for anchor in self.anchors():
            haystack = " ".join(
                str(anchor.get(key, ""))
                for key in ("anchor_id", "body", "surface_id", "object_id")
            ).lower()
            if text and text not in haystack:
                continue
            if status != "all" and anchor.get("status") != status:
                continue
            if surface and surface not in str(anchor.get("surface_id", "")).lower():
                continue
            out.append(anchor)
        return out

    def select_anchor(self, anchor_id: str | None) -> str | None:
        if not anchor_id:
            return None
        if self._anchor_obj(anchor_id) is None:
            self.state.last_error = f"anchor not found: {anchor_id}"
            return None
        if self.selected_anchor_id == anchor_id:
            self.state.last_error = None
            return anchor_id
        self.selected_anchor_id = anchor_id
        self.state.selected_anchor_id = anchor_id
        self.state.last_error = None
        self.reload_overlay()
        if callable(self.on_change):
            self.on_change()
        return anchor_id

    def select_relative(self, offset: int, *, text: str = "", status: str = "all", surface: str = "") -> str | None:
        anchors = self.filter_anchors(text=text, status=status, surface=surface)
        if not anchors:
            self.state.last_error = "no matching anchors"
            return None
        ids = [str(anchor.get("anchor_id")) for anchor in anchors]
        current = self.selected_anchor_id if self.selected_anchor_id in ids else ids[0]
        index = ids.index(current)
        return self.select_anchor(ids[(index + offset) % len(ids)])

    def select_first_status(self, status: str) -> str | None:
        anchors = self.filter_anchors(status=status)
        return self.select_anchor(str(anchors[0].get("anchor_id"))) if anchors else None

    def selected_info_text(self) -> str:
        anchor = self._anchor_obj()
        record = self._anchor_record()
        if anchor is None or record is None:
            return "No anchor selected."
        warnings = anchor.get("warnings") or []
        coords = anchor.get("surface_coordinates") or record.surface_coordinates or {}
        lines = [
            f"anchor_id: {record.anchor_id}",
            f"body: {record.body}",
            f"frames: {record.start_frame} -> {record.end_frame}",
            f"surface_id: {record.surface_id}",
            f"object_id: {record.object_id}",
            f"surface_type: {record.surface_type}",
            f"world_position: {record.world_position}",
            f"surface_coordinates: u={coords.get('u')} v={coords.get('v')}",
            f"surface_bounds: {record.surface_bounds}",
            f"status: {anchor.get('status')}",
            f"warnings: {warnings}",
            f"surface_binding_source: {record.surface_binding_source}",
            "binding_granularity: anchor_point",
            f"pending_edits: {len(self.pending_edits())}",
            f"last_message: {self.state.last_message or ''}",
            f"last_error: {self.state.last_error or ''}",
        ]
        return "\n".join(lines)

    def current_surface_uv(self) -> tuple[float, float] | None:
        record = self._anchor_record()
        coords = record.surface_coordinates if record is not None else None
        if not coords:
            return None
        return float(coords.get("u", 0.0)), float(coords.get("v", 0.0))

    def move_selected(self, *, tangent_delta: list[float], mode: str) -> dict[str, Any]:
        if not self.selected_anchor_id:
            raise ValueError("no anchor selected")
        before = self._snapshot()
        try:
            result = apply_direct_anchor_move(
                self.state,
                anchor_id=self.selected_anchor_id,
                tangent_delta=tangent_delta,
                mode=mode,
            )
        except Exception as exc:
            self.state.last_error = str(exc)
            self._restore(before)
            raise
        self.undo_stack.append(before)
        self.redo_stack.clear()
        self.reload_overlay()
        return result

    def move_selected_to_uv(self, *, target_u: float, target_v: float, mode: str) -> dict[str, Any]:
        current = self.current_surface_uv()
        if current is None:
            raise ValueError("selected anchor has no surface coordinates")
        du = float(target_u) - current[0]
        dv = float(target_v) - current[1]
        return self.move_selected(tangent_delta=[du, dv], mode=mode)

    def restore_anchor_to_initial(self, anchor_id: str | None = None, *, mode: str = "reject", eps: float = 1e-6) -> dict[str, Any]:
        target = anchor_id or self.selected_anchor_id
        if not target:
            raise ValueError("no anchor selected")
        self.select_anchor(target)
        current = self._anchor_record(target)
        original = self._original_anchor_record(target)
        if current is None or original is None:
            raise ValueError(f"anchor initial state not found: {target}")
        if current.surface_id != original.surface_id or current.object_id != original.object_id:
            raise ValueError("cannot restore across a different contact surface")
        current_uv = current.surface_coordinates or {}
        original_uv = original.surface_coordinates or {}
        if "u" in original_uv and "v" in original_uv:
            du = float(original_uv["u"]) - float(current_uv.get("u", 0.0))
            dv = float(original_uv["v"]) - float(current_uv.get("v", 0.0))
        elif original.world_position is not None:
            du, dv = self.tangent_delta_from_world_request(current, original.world_position)
        else:
            raise ValueError("initial anchor has no surface coordinates or world position")
        if abs(du) < eps and abs(dv) < eps:
            self.state.last_message = f"{target} already at initial position"
            self.state.last_error = None
            return {"no_op": True, "anchor_id": target, "tangent_delta": [0.0, 0.0]}
        result = self.move_selected(tangent_delta=[du, dv], mode=mode)
        pending = self.pending_edits()
        if pending:
            latest = pending[-1]
            metadata = dict(latest.metadata)
            metadata.update(
                {
                    "surface_editor_action": "restore_initial_position",
                    "restored_from_initial_anchor": True,
                }
            )
            pending[-1] = replace(latest, metadata=metadata, source="viser_surface_editor")
            write_pending_surface_edits(self.state.session, pending)
        self.state.last_message = f"restored {target} to initial position"
        self.reload_overlay()
        return result

    def tangent_delta_from_world_request(self, record: ContactAnchorRecord, requested_world_position: list[float] | tuple[float, float, float]) -> tuple[float, float]:
        if not record.surface_id or record.surface_origin is None or record.surface_tangent_u is None or record.surface_tangent_v is None:
            raise ValueError("anchor is not surface-bound; bind surfaces first")
        if not record.surface_coordinates:
            raise ValueError("anchor has no surface coordinates")
        requested = np.asarray(requested_world_position, dtype=float)
        origin = np.asarray(record.surface_origin, dtype=float)
        tangent_u = np.asarray(record.surface_tangent_u, dtype=float)
        tangent_v = np.asarray(record.surface_tangent_v, dtype=float)
        local = requested - origin
        requested_u = float(np.dot(local, tangent_u))
        requested_v = float(np.dot(local, tangent_v))
        old_u = float(record.surface_coordinates.get("u", 0.0))
        old_v = float(record.surface_coordinates.get("v", 0.0))
        return requested_u - old_u, requested_v - old_v

    def projected_world_request(self, record: ContactAnchorRecord, requested_world_position: list[float] | tuple[float, float, float]) -> list[float]:
        if record.surface_origin is None or record.surface_tangent_u is None or record.surface_tangent_v is None:
            raise ValueError("anchor has no surface basis")
        du, dv = self.tangent_delta_from_world_request(record, requested_world_position)
        old_u = float((record.surface_coordinates or {}).get("u", 0.0))
        old_v = float((record.surface_coordinates or {}).get("v", 0.0))
        origin = np.asarray(record.surface_origin, dtype=float)
        tangent_u = np.asarray(record.surface_tangent_u, dtype=float)
        tangent_v = np.asarray(record.surface_tangent_v, dtype=float)
        return (origin + tangent_u * (old_u + du) + tangent_v * (old_v + dv)).tolist()

    def drag_selected_to_world(self, requested_world_position: list[float] | tuple[float, float, float], *, mode: str, eps: float = 1e-6) -> dict[str, Any]:
        record = self._anchor_record()
        if record is None:
            raise ValueError("no anchor selected")
        old_surface_id = record.surface_id
        old_object_id = record.object_id
        du, dv = self.tangent_delta_from_world_request(record, requested_world_position)
        if abs(du) < eps and abs(dv) < eps:
            self.state.last_error = None
            self.state.last_message = "normal-only drag ignored"
            return {"no_op": True, "anchor_id": record.anchor_id, "tangent_delta": [0.0, 0.0]}
        result = self.move_selected(tangent_delta=[du, dv], mode=mode)
        moved = self._anchor_record()
        if moved is None:
            raise ValueError("moved anchor disappeared")
        if moved.surface_id != old_surface_id or moved.object_id != old_object_id:
            raise ValueError("drag attempted to switch contact surface")
        return result

    def undo(self) -> bool:
        if not self.undo_stack:
            self.state.last_message = "nothing to undo"
            return False
        current = self._snapshot()
        previous = self.undo_stack.pop()
        self.redo_stack.append(current)
        self._restore(previous)
        self.state.last_message = "undone"
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            self.state.last_message = "nothing to redo"
            return False
        current = self._snapshot()
        next_snapshot = self.redo_stack.pop()
        self.undo_stack.append(current)
        self._restore(next_snapshot)
        self.state.last_message = "redone"
        return True

    def reset(self) -> None:
        if self.original_graph is None:
            raise ValueError("original graph is unavailable")
        self.undo_stack.append(self._snapshot())
        self.redo_stack.clear()
        write_surface_editor_graph(self.state.session, copy.deepcopy(self.original_graph))
        write_pending_surface_edits(self.state.session, [])
        self.state.last_message = "reset session"
        self.reload_overlay()

    def discard(self) -> None:
        self.reset()
        self.state.last_message = "discarded unsaved edits"

    def save(self, *, layers_root: Path = LAYERS_ROOT) -> Path | None:
        return save_editor_state(self.state, layers_root=layers_root)

    def reload_overlay(self) -> dict[str, Any]:
        self.state.render_generation += 1
        self.last_overlay = load_surface_overlay(self.state.overlay_path)
        if self.server is not None:
            _remove_handles(self.render_handles)
            self.render_handles = _render_overlay(
                self.server,
                self.last_overlay,
                namespace=f"/surface_editor/render_{self.state.render_generation:06d}",
                selected_anchor_id=self.selected_anchor_id,
                controller=self,
                edit_mode=self.edit_mode,
            )
        return self.last_overlay


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


def _anchor_color(obj: dict[str, Any]) -> tuple[int, int, int]:
    status = str(obj.get("status", ""))
    if status in STATUS_COLOR_OVERRIDES:
        return _color(status)
    explicit = obj.get("color")
    if isinstance(explicit, list) and len(explicit) == 3:
        return tuple(int(value) for value in explicit)
    body = str(obj.get("body", "")).lower()
    for key, color in BODY_COLORS.items():
        if key in body or body in key:
            return color
    return _color(status)


def _remove_handles(handles: list[Any]) -> None:
    for handle in handles:
        remove = getattr(handle, "remove", None)
        if callable(remove):
            remove()


def _anchor_patch_mesh(record: ContactAnchorRecord, *, radius: float = 0.045, normal_offset: float = 0.002, segments: int = 24) -> tuple[np.ndarray, np.ndarray] | None:
    if record.world_position is None or record.surface_tangent_u is None or record.surface_tangent_v is None:
        return None
    center = np.asarray(record.world_position, dtype=float)
    tangent_u = np.asarray(record.surface_tangent_u, dtype=float)
    tangent_v = np.asarray(record.surface_tangent_v, dtype=float)
    if record.surface_normal is not None:
        center = center + np.asarray(record.surface_normal, dtype=float) * normal_offset
    vertices = [center]
    for index in range(segments):
        angle = 2.0 * np.pi * float(index) / float(segments)
        vertices.append(center + tangent_u * np.cos(angle) * radius + tangent_v * np.sin(angle) * radius)
    faces = [[0, index, 1 + (index % segments)] for index in range(1, segments + 1)]
    vertices = np.asarray(vertices, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.uint32)
    return vertices, faces


def _anchor_positions_differ(first: ContactAnchorRecord | None, second: ContactAnchorRecord | None, *, eps: float = 1e-6) -> bool:
    if first is None or second is None or first.world_position is None or second.world_position is None:
        return False
    return bool(np.linalg.norm(np.asarray(first.world_position, dtype=float) - np.asarray(second.world_position, dtype=float)) > eps)


def _selected_tangent_arrows(record: ContactAnchorRecord, *, length: float = 0.2) -> tuple[np.ndarray, np.ndarray] | None:
    if record.world_position is None or record.surface_tangent_u is None or record.surface_tangent_v is None:
        return None
    start = np.asarray(record.world_position, dtype=float)
    if record.surface_normal is not None:
        start = start + np.asarray(record.surface_normal, dtype=float) * 0.006
    tangent_u = np.asarray(record.surface_tangent_u, dtype=float)
    tangent_v = np.asarray(record.surface_tangent_v, dtype=float)
    points = np.asarray(
        [
            [start, start + tangent_u * length],
            [start, start + tangent_v * length],
        ],
        dtype=np.float32,
    )
    colors = np.asarray(
        [
            (255, 90, 90),
            (90, 255, 120),
        ],
        dtype=np.uint8,
    )
    return points, colors


def _render_overlay(
    server: Any,
    overlay: dict[str, Any],
    *,
    namespace: str = "/surface_editor",
    selected_anchor_id: str | None = None,
    controller: SurfaceEditorController | None = None,
    edit_mode: str = "direct",
) -> list[Any]:
    handles: list[Any] = []

    for obj in overlay.get("objects", []):
        obj_type = obj.get("type")
        status = str(obj.get("status", "bound"))
        color = _color(status)
        if obj_type == "surface_quad":
            continue
        elif obj_type == "normal_axis":
            continue
        elif obj_type == "projection_line":
            continue
        elif obj_type == "anchor_point":
            color = _anchor_color(obj)
            anchor_id = str(obj.get("anchor_id", ""))
            anchor_name = _safe_name(anchor_id or "anchor")
            record = controller._anchor_record(anchor_id) if controller is not None else None
            original_record = controller._original_anchor_record(anchor_id) if controller is not None else None
            marker = None
            if (
                controller is not None
                and original_record is not None
                and _anchor_positions_differ(record, original_record)
            ):
                original_mesh = _anchor_patch_mesh(original_record, radius=0.043, normal_offset=0.001)
                if original_mesh is not None and hasattr(server.scene, "add_mesh_simple"):
                    vertices, faces = original_mesh
                    original_marker = server.scene.add_mesh_simple(
                        f"{namespace}/anchors/{anchor_name}_initial_ghost",
                        vertices=vertices,
                        faces=faces,
                        color=color,
                        opacity=0.28,
                        side="double",
                    )
                    handles.append(original_marker)

                    @original_marker.on_click
                    def _(_, anchor_id: str = anchor_id) -> None:
                        try:
                            result = controller.restore_anchor_to_initial(anchor_id)
                            print(f"[surface editor] restored anchor={anchor_id} result={result}")
                            if callable(controller.on_change):
                                controller.on_change()
                        except Exception as exc:
                            controller.state.last_error = str(exc)
                            if callable(controller.on_change):
                                controller.on_change()
                            print(f"[surface editor] restore failed anchor={anchor_id}: {exc}")

            mesh = _anchor_patch_mesh(record) if record is not None else None
            if mesh is not None and hasattr(server.scene, "add_mesh_simple"):
                vertices, faces = mesh
                patch_color = STATUS_COLORS["selected"] if selected_anchor_id and anchor_id == selected_anchor_id else color
                marker = server.scene.add_mesh_simple(
                    f"{namespace}/anchors/{anchor_name}_patch",
                    vertices=vertices,
                    faces=faces,
                    color=patch_color,
                    opacity=0.9,
                    side="double",
                )
                handles.append(marker)
            else:
                marker = server.scene.add_frame(
                    f"{namespace}/anchors/{anchor_name}",
                    show_axes=False,
                    origin_radius=0.045,
                    origin_color=color,
                    position=np.asarray(obj["position"], dtype=np.float32),
                )
                handles.append(marker)
            if controller is not None:
                @marker.on_click
                def _(_, anchor_id: str = anchor_id) -> None:
                    controller.select_anchor(anchor_id)
                    print(f"[surface editor] selected anchor={anchor_id}")

    if controller is not None and selected_anchor_id:
        record = controller._anchor_record(selected_anchor_id)
        if record is not None and record.world_position is not None:
            arrows = _selected_tangent_arrows(record)
            if arrows is not None and hasattr(server.scene, "add_arrows"):
                points, colors = arrows
                handle = server.scene.add_arrows(
                    f"{namespace}/selected_anchor_tangent_arrows",
                    points=points,
                    colors=colors,
                    shaft_radius=0.008,
                    head_radius=0.025,
                    head_length=0.045,
                    visible=True,
                )
                handles.append(handle)
    return handles


def _load_motion_points(path: str | Path) -> np.ndarray:
    qpos, _fps = load_motion_sequence(path)
    if qpos.ndim != 2 or qpos.shape[1] < 3:
        return np.zeros((0, 3), dtype=np.float32)
    return np.asarray(qpos[:, :3], dtype=np.float32)


def load_motion_sequence(path: str | Path) -> tuple[np.ndarray, int]:
    data = np.load(path, allow_pickle=True)
    fps = int(np.asarray(data["fps"]).reshape(-1)[0]) if "fps" in data else 50
    if "qpos" in data:
        qpos = np.asarray(data["qpos"])
    elif "joint_pos" in data:
        qpos = np.asarray(data["joint_pos"])
    else:
        raise KeyError(f"{path} has neither qpos nor joint_pos")
    if qpos.ndim != 2:
        raise ValueError(f"{path} motion array must be [T,D], got {qpos.shape}")
    return np.asarray(qpos, dtype=np.float32), fps


def _add_static_urdf(server: Any, *, root_name: str, urdf_path: str | Path) -> list[Any]:
    try:
        import yourdfpy  # type: ignore[import-untyped]
        from viser.extras import ViserUrdf  # type: ignore[import-not-found]
    except ImportError:
        return []
    root = server.scene.add_frame(root_name, show_axes=False)
    urdf = yourdfpy.URDF.load(str(urdf_path), load_meshes=True, build_scene_graph=True)
    viser_urdf = ViserUrdf(server, urdf_or_path=urdf, root_node_name=root_name)
    return [root, viser_urdf]


def _add_motion_playback(
    server: Any,
    *,
    qpos: np.ndarray,
    fps: int,
    robot_urdf: str | Path | None,
    object_urdf: str | Path | None = None,
) -> list[Any]:
    handles: list[Any] = []
    if object_urdf:
        object_path = Path(object_urdf)
        if object_path.exists():
            handles.extend(_add_static_urdf(server, root_name="/object", urdf_path=object_path))
    if robot_urdf is None or not Path(robot_urdf).exists():
        print("[surface editor] robot_urdf missing; showing root trace only")
        return handles
    try:
        import yourdfpy  # type: ignore[import-untyped]
        from viser.extras import ViserUrdf  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"[surface editor] robot playback unavailable: {exc}")
        return handles

    robot_root = server.scene.add_frame("/robot", show_axes=False)
    robot = yourdfpy.URDF.load(str(robot_urdf), load_meshes=True, build_scene_graph=True)
    viser_robot = ViserUrdf(server, urdf_or_path=robot, root_node_name="/robot")
    robot_dof = len(viser_robot.get_actuated_joint_limits())
    handles.extend([robot_root, viser_robot])
    n_frames = int(qpos.shape[0])
    playing = {"value": False}
    current_frame = {"value": 0.0}
    stop_flag = {"value": False}

    def _apply_frame(index: int) -> None:
        if n_frames == 0:
            return
        frame = int(np.clip(index, 0, n_frames - 1))
        q = qpos[frame]
        if q.shape[0] >= 3:
            robot_root.position = tuple(float(v) for v in q[:3])
        if q.shape[0] >= 7:
            robot_root.wxyz = tuple(float(v) for v in q[3:7])
        if q.shape[0] >= 7 + robot_dof:
            viser_robot.update_cfg(q[7 : 7 + robot_dof])

    with server.gui.add_folder("Motion Playback"):
        frame_slider = server.gui.add_slider("frame", min=0, max=max(0, n_frames - 1), step=1, initial_value=0)
        play_btn = server.gui.add_button("Play / Pause")
        fps_in = server.gui.add_number("fps", initial_value=int(fps), min=1, max=240, step=1)
        loop_cb = server.gui.add_checkbox("loop", initial_value=True)

    @frame_slider.on_update
    def _(_) -> None:
        frame = int(np.clip(int(frame_slider.value), 0, max(0, n_frames - 1)))
        current_frame["value"] = float(frame)
        _apply_frame(frame)

    @play_btn.on_click
    def _(_) -> None:
        playing["value"] = not playing["value"]

    def _play_loop() -> None:
        tick = time.perf_counter()
        while not stop_flag["value"]:
            if not playing["value"] or n_frames <= 1:
                time.sleep(0.03)
                tick = time.perf_counter()
                continue
            now = time.perf_counter()
            dt = max(0.0, now - tick)
            tick = now
            current_frame["value"] += dt * float(fps_in.value)
            if current_frame["value"] >= n_frames:
                if bool(loop_cb.value):
                    current_frame["value"] %= n_frames
                else:
                    current_frame["value"] = float(n_frames - 1)
                    playing["value"] = False
            frame = int(np.clip(round(current_frame["value"]), 0, n_frames - 1))
            frame_slider.value = frame
            _apply_frame(frame)
            time.sleep(0.01)

    _apply_frame(0)
    thread = threading.Thread(target=_play_loop, daemon=True)
    thread.start()
    return handles


def run_surface_overlay_player(args: argparse.Namespace) -> None:
    try:
        import viser  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit("viser is not installed in this environment; use surface-editor fallback/sync commands") from exc

    state = load_editor_state(args.surface_editor_session)
    overlay = load_surface_overlay(args.surface_binding_overlay)
    server = viser.ViserServer(port=args.viser_port or args.timeline_port)
    server.gui.configure_theme(control_layout="fixed", control_width="large", dark_mode=True, show_logo=False, show_share_button=False)
    server.scene.add_grid("/grid", width=8.0, height=8.0, position=(0.0, 0.0, 0.0))

    qpos, motion_fps = load_motion_sequence(args.qpos_npz)
    _add_motion_playback(
        server,
        qpos=qpos,
        fps=int(args.fps or motion_fps),
        robot_urdf=args.robot_urdf,
        object_urdf=args.object_urdf if args.with_terrain else None,
    )
    motion_points = qpos[:, :3] if qpos.shape[1] >= 3 else np.zeros((0, 3), dtype=np.float32)
    if motion_points.shape[0] > 1:
        server.scene.add_line_segments(
            "/motion/root_path",
            points=np.stack([motion_points[:-1], motion_points[1:]], axis=1),
            colors=np.full((motion_points.shape[0] - 1, 2, 3), 160, dtype=np.uint8),
            line_width=1.5,
            visible=True,
        )
    controller = SurfaceEditorController.create(server, state)
    controller.edit_mode = args.edit_mode
    if args.select_anchor:
        controller.select_anchor(args.select_anchor)
    anchor_ids = [str(anchor.get("anchor_id", "")) for anchor in controller.anchors() if anchor.get("anchor_id")]
    selected_default = controller.selected_anchor_id or (anchor_ids[0] if anchor_ids else "")

    with server.gui.add_folder("Surface Anchor Editor"):
        anchor_filter = server.gui.add_text("filter", initial_value="")
        surface_filter = server.gui.add_text("surface_filter", initial_value="")
        status_filter = server.gui.add_dropdown(
            "status_filter",
            options=("all", "bound", "edited", "clamped", "suspicious", "failed", "unbound"),
            initial_value=args.show_only,
        )
        anchor_id = server.gui.add_text("anchor_id", initial_value=selected_default)
        du = server.gui.add_number("du", initial_value=0.0, step=0.01)
        dv = server.gui.add_number("dv", initial_value=0.0, step=0.01)
        step_size = server.gui.add_number("step_size", initial_value=float(args.step_size), step=0.005)
        target_u = server.gui.add_number("target_u", initial_value=0.0, step=0.01)
        target_v = server.gui.add_number("target_v", initial_value=0.0, step=0.01)
        mode = server.gui.add_dropdown("mode", options=("reject", "clamp"), initial_value=args.default_mode)
        move_btn = server.gui.add_button("Move anchor" if args.edit_mode == "direct" else "Write move request")
        move_to_uv_btn = server.gui.add_button("Move to u/v")
        plus_u_btn = server.gui.add_button("+u")
        minus_u_btn = server.gui.add_button("-u")
        plus_v_btn = server.gui.add_button("+v")
        minus_v_btn = server.gui.add_button("-v")
        prev_btn = server.gui.add_button("Select previous")
        next_btn = server.gui.add_button("Select next")
        find_btn = server.gui.add_button("Find anchors")
        first_suspicious_btn = server.gui.add_button("First suspicious")
        first_unbound_btn = server.gui.add_button("First unbound")
        first_edited_btn = server.gui.add_button("First edited")
        undo_btn = server.gui.add_button("Undo")
        redo_btn = server.gui.add_button("Redo")
        reset_btn = server.gui.add_button("Reset session")
        discard_btn = server.gui.add_button("Discard unsaved edits")
        request_btn = server.gui.add_button("Write request only")
        reload_btn = server.gui.add_button("Reload overlay")
        save_btn = server.gui.add_button("Save edits")
        status_text = server.gui.add_text("status", initial_value="ready")
        matches_text = server.gui.add_text("matches", initial_value="")
        info_text = server.gui.add_text("selected_info", initial_value=controller.selected_info_text())

    def _filters() -> dict[str, str]:
        return {
            "text": str(anchor_filter.value),
            "status": str(status_filter.value),
            "surface": str(surface_filter.value),
        }

    def _sync_selected_fields() -> None:
        anchor_id.value = controller.selected_anchor_id or ""
        current = controller.current_surface_uv()
        if current is not None:
            target_u.value = current[0]
            target_v.value = current[1]
        info_text.value = controller.selected_info_text()

    controller.on_change = _sync_selected_fields
    controller.drag_mode_getter = lambda: str(mode.value)

    def _set_status(text: str) -> None:
        status_text.value = text
        info_text.value = controller.selected_info_text()

    def _refresh_and_sync() -> None:
        controller.reload_overlay()
        _sync_selected_fields()

    def _move_delta(delta: list[float]) -> None:
        if args.edit_mode == "request":
            if not str(anchor_id.value).strip():
                _set_status("error: no anchor_id selected")
                return
            request = append_move_request(
                args.surface_editor_requests,
                anchor_id=str(anchor_id.value).strip(),
                tangent_delta=delta,
                mode=str(mode.value),
            )
            _set_status(f"request written: {request['request_id']}")
            print(f"[surface editor] wrote request {request['request_id']} anchor={request['anchor_id']}")
            return
        try:
            if str(anchor_id.value).strip() != controller.selected_anchor_id:
                controller.select_anchor(str(anchor_id.value).strip())
            result = controller.move_selected(tangent_delta=delta, mode=str(mode.value))
            _refresh_and_sync()
            _set_status(f"moved {result['anchor_id']} delta={result['delta_world']}")
            print(f"[surface editor] moved anchor={result['anchor_id']} edit={result['edit_id']}")
        except Exception as exc:
            state.last_error = str(exc)
            _set_status(f"error: {exc}")
            print(f"[surface editor] move failed anchor={anchor_id.value}: {exc}")

    @move_btn.on_click
    def _(_) -> None:
        if not str(anchor_id.value).strip():
            print("[surface editor] no anchor_id selected")
            status_text.value = "error: no anchor_id selected"
            return
        _move_delta([float(du.value), float(dv.value)])

    @move_to_uv_btn.on_click
    def _(_) -> None:
        try:
            if str(anchor_id.value).strip() != controller.selected_anchor_id:
                controller.select_anchor(str(anchor_id.value).strip())
            if args.edit_mode == "request":
                current = controller.current_surface_uv()
                if current is None:
                    raise ValueError("selected anchor has no surface coordinates")
                _move_delta([float(target_u.value) - current[0], float(target_v.value) - current[1]])
                return
            result = controller.move_selected_to_uv(
                target_u=float(target_u.value),
                target_v=float(target_v.value),
                mode=str(mode.value),
            )
            _refresh_and_sync()
            _set_status(f"moved {result['anchor_id']} delta={result['delta_world']}")
            print(f"[surface editor] moved anchor={result['anchor_id']} edit={result['edit_id']}")
        except Exception as exc:
            state.last_error = str(exc)
            _set_status(f"error: {exc}")
            print(f"[surface editor] move failed anchor={anchor_id.value}: {exc}")

    @plus_u_btn.on_click
    def _(_) -> None:
        _move_delta([float(step_size.value), 0.0])

    @minus_u_btn.on_click
    def _(_) -> None:
        _move_delta([-float(step_size.value), 0.0])

    @plus_v_btn.on_click
    def _(_) -> None:
        _move_delta([0.0, float(step_size.value)])

    @minus_v_btn.on_click
    def _(_) -> None:
        _move_delta([0.0, -float(step_size.value)])

    @find_btn.on_click
    def _(_) -> None:
        matches = controller.filter_anchors(**_filters())
        matches_text.value = "\n".join(str(item.get("anchor_id")) for item in matches[:20]) or "<none>"
        if matches:
            controller.select_anchor(str(matches[0].get("anchor_id")))
            _refresh_and_sync()
        _set_status(f"matches={len(matches)}")

    @prev_btn.on_click
    def _(_) -> None:
        controller.select_relative(-1, **_filters())
        _refresh_and_sync()
        _set_status(f"selected {controller.selected_anchor_id}")

    @next_btn.on_click
    def _(_) -> None:
        controller.select_relative(1, **_filters())
        _refresh_and_sync()
        _set_status(f"selected {controller.selected_anchor_id}")

    @first_suspicious_btn.on_click
    def _(_) -> None:
        controller.select_first_status("suspicious")
        _refresh_and_sync()
        _set_status(f"selected {controller.selected_anchor_id}")

    @first_unbound_btn.on_click
    def _(_) -> None:
        controller.select_first_status("unbound")
        _refresh_and_sync()
        _set_status(f"selected {controller.selected_anchor_id}")

    @first_edited_btn.on_click
    def _(_) -> None:
        controller.select_first_status("edited")
        _refresh_and_sync()
        _set_status(f"selected {controller.selected_anchor_id}")

    @undo_btn.on_click
    def _(_) -> None:
        controller.undo()
        _refresh_and_sync()
        _set_status(controller.state.last_message or "undo")

    @redo_btn.on_click
    def _(_) -> None:
        controller.redo()
        _refresh_and_sync()
        _set_status(controller.state.last_message or "redo")

    @reset_btn.on_click
    def _(_) -> None:
        try:
            controller.reset()
            _refresh_and_sync()
            _set_status("reset session")
        except Exception as exc:
            state.last_error = str(exc)
            _set_status(f"reset error: {exc}")

    @discard_btn.on_click
    def _(_) -> None:
        try:
            controller.discard()
            _refresh_and_sync()
            _set_status("discarded unsaved edits")
        except Exception as exc:
            state.last_error = str(exc)
            _set_status(f"discard error: {exc}")

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
        next_overlay = controller.reload_overlay()
        _sync_selected_fields()
        _set_status(f"reloaded overlay objects={len(next_overlay.get('objects', []))}")

    @save_btn.on_click
    def _(_) -> None:
        try:
            out = controller.save()
            _set_status(f"saved: {out}")
            print(f"[surface editor] saved output_contact_layer={out}")
        except Exception as exc:
            state.last_error = str(exc)
            _set_status(f"save error: {exc}")
            print(f"[surface editor] save failed: {exc}")

    controller.reload_overlay()
    _sync_selected_fields()

    print(f"[surface editor] overlay={args.surface_binding_overlay}")
    print(f"[surface editor] session={args.surface_editor_session}")
    print(f"[surface editor] requests={args.surface_editor_requests}")
    print(f"[surface editor] edit_mode={args.edit_mode}")
    print(f"[surface editor] robot_urdf={args.robot_urdf or 'none'}")
    print(f"[surface editor] object_urdf={args.object_urdf if args.with_terrain else 'none'}")
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
    parser.add_argument("--step-size", type=float, default=0.02)
    parser.add_argument("--default-mode", choices=("reject", "clamp"), default="reject")
    parser.add_argument("--show-only", choices=("all", "bound", "edited", "clamped", "suspicious", "failed", "unbound"), default="all")
    parser.add_argument("--select-anchor", default=None)
    parser.add_argument("--viser-port", type=int, default=None)
    parser.add_argument("--timeline-port", type=int, default=8094)
    parser.add_argument("--fps", type=int, default=50)
    parser.add_argument("--robot-urdf", default=None)
    parser.add_argument("--object-urdf", default=None)
    parser.add_argument("--with-terrain", action="store_true")
    return parser


def main() -> None:
    run_surface_overlay_player(build_arg_parser().parse_args())


if __name__ == "__main__":
    main()
