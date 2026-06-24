from __future__ import annotations

import argparse
import copy
import json
import os
import socket
import sys
import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact.graph import ContactGraph
from motion_edit.generation import apply_contact_edit_plan_to_motion
from motion_edit.contact.plans import ContactEditPlan, read_contact_edit_plan, validate_contact_edit_plan, write_contact_edit_plan
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.paths import LAYERS_ROOT, MOTIONS_ROOT, WORKBENCH_ROOT
from motion_edit.storage.io import read_motion_asset
from motion_edit.viewer.contact_timeline import start_contact_timeline_wrapper
from motion_edit.workbench import (
    coalesce_pending_surface_edits,
    move_surface_editor_anchor,
    read_pending_surface_edits,
    read_surface_editor_graph,
    read_surface_editor_session,
    save_surface_editor_session,
    write_pending_surface_edits,
    write_surface_editor_graph,
)
from motion_edit.workbench.contact_editor_setup import ContactEditorConfig, infer_terrain_urdf, prepare_contact_editor_session as prepare_contact_editor_workbench_session
from motion_edit.workbench.recent import RecentMotionEntry, recent_entry_labels, read_recent_motions, upsert_recent_motion
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

FOOT_PATCH_ROLE_COLORS: dict[str, tuple[int, int, int]] = {
    "toe": (255, 185, 70),
    "heel": (105, 175, 255),
}

FOOT_PATCH_ROLE_RADII: dict[str, float] = {
    "toe": 0.032,
    "heel": 0.04,
    "sole": 0.052,
}


def _port_is_available(port: int, *, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, int(port)))
        except OSError:
            return False
    return True


def _require_available_port(port: int, *, label: str) -> None:
    if not _port_is_available(port):
        raise RuntimeError(
            f"{label} port {port} is already in use; close the existing contact editor before starting a new one"
        )


def _assert_viser_port(server: Any, expected_port: int) -> None:
    actual_port = int(getattr(server, "port", expected_port))
    if actual_port != int(expected_port):
        stop = getattr(server, "stop", None)
        if callable(stop):
            stop()
        raise RuntimeError(
            f"Viser moved from requested port {expected_port} to {actual_port}; "
            "close the existing contact editor instead of using a new port"
        )


@dataclass
class MotionPlaybackController:
    n_frames: int
    current_frame: dict[str, float]
    playing: dict[str, bool]
    apply_frame: Any
    frame_slider: Any
    frame_text: Any
    stop_callback: Any | None = None
    frame_change_callback: Any | None = None

    def frame(self) -> int:
        return int(np.clip(round(float(self.current_frame["value"])), 0, max(0, self.n_frames - 1)))

    def set_frame(self, frame: int) -> None:
        next_frame = int(np.clip(frame, 0, max(0, self.n_frames - 1)))
        self.current_frame["value"] = float(next_frame)
        self.frame_slider.value = next_frame
        self.apply_frame(next_frame)
        self.frame_text.value = f"{next_frame} / {max(0, self.n_frames - 1)}"
        if callable(self.frame_change_callback):
            self.frame_change_callback(next_frame)

    def step(self, amount: int) -> None:
        self.set_frame(self.frame() + int(amount))

    def toggle(self) -> None:
        self.playing["value"] = not self.playing["value"]

    def stop(self) -> None:
        if callable(self.stop_callback):
            self.stop_callback()
        self.playing["value"] = False


@dataclass
class ReloadablePlayback:
    current: MotionPlaybackController | None = None

    @property
    def n_frames(self) -> int:
        return self.current.n_frames if self.current is not None else 0

    @property
    def playing(self) -> dict[str, bool]:
        return self.current.playing if self.current is not None else {"value": False}

    def frame(self) -> int:
        return self.current.frame() if self.current is not None else 0

    def set_frame(self, frame: int) -> None:
        if self.current is not None:
            self.current.set_frame(frame)

    def step(self, amount: int) -> None:
        if self.current is not None:
            self.current.step(amount)

    def toggle(self) -> None:
        if self.current is not None:
            self.current.toggle()

    def replace(self, playback: MotionPlaybackController | None) -> None:
        if self.current is not None:
            self.current.stop()
        self.current = playback


@dataclass
class GenerationJobState:
    running: bool = False
    last_output_motion: str | None = None
    last_error: str | None = None
    last_started_at: float | None = None
    last_finished_at: float | None = None


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
    current_frame_getter: Any = None
    reload_motion_callback: Any = None
    timeline_port: int = 8094
    default_mode: str = "reject"
    show_only: str = "all"
    show_all_anchors: bool = False
    fps: int = 50
    robot_urdf: str | None = None
    terrain_urdf: str | None = None
    _last_anchor_render_frame: int | None = None
    _last_anchor_render_time: float = 0.0

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

    def filter_anchors(
        self,
        *,
        text: str = "",
        status: str = "all",
        surface: str = "",
        current_only: bool = False,
    ) -> list[dict[str, Any]]:
        text = text.strip().lower()
        surface = surface.strip().lower()
        current_frame = int(self.current_frame_getter()) if current_only and callable(self.current_frame_getter) else None
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
            if current_frame is not None:
                record = self._anchor_record(str(anchor.get("anchor_id")))
                if record is None or not (record.start_frame <= current_frame <= record.end_frame):
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

    def select_relative(
        self,
        offset: int,
        *,
        text: str = "",
        status: str = "all",
        surface: str = "",
        current_only: bool = False,
    ) -> str | None:
        anchors = self.filter_anchors(text=text, status=status, surface=surface, current_only=current_only)
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
        patch_role = record.metadata.get("patch_role") or anchor.get("patch_role") or "-"
        lines = [
            f"anchor_id: {record.anchor_id}",
            f"body: {record.body}  role: {patch_role}",
            f"frames: {record.start_frame} -> {record.end_frame}",
            f"surface: {record.surface_id}  object: {record.object_id}",
            f"uv: u={coords.get('u')} v={coords.get('v')}",
            f"status: {anchor.get('status')}",
            f"warnings: {warnings}",
            f"pending_edits: {len(self.pending_edits())}",
        ]
        if self.state.last_error:
            lines.append(f"last_error: {self.state.last_error}")
        elif self.state.last_message:
            lines.append(f"last_message: {self.state.last_message}")
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
        if callable(self.current_frame_getter):
            self._last_anchor_render_frame = int(self.current_frame_getter())
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

    def should_render_anchor(self, anchor_id: str, obj: dict[str, Any]) -> bool:
        if self.show_all_anchors:
            return True
        if self.selected_anchor_id and anchor_id == self.selected_anchor_id:
            return True
        if not callable(self.current_frame_getter):
            return True
        current_frame = int(self.current_frame_getter())
        start = obj.get("start_frame")
        end = obj.get("end_frame")
        if start is None or end is None:
            record = self._anchor_record(anchor_id)
            if record is None:
                return True
            start, end = record.start_frame, record.end_frame
        return int(start) <= current_frame <= int(end)

    def on_frame_changed(self, frame: int) -> None:
        if self.show_all_anchors:
            return
        next_frame = int(frame)
        if self._last_anchor_render_frame == next_frame:
            return
        now = time.perf_counter()
        if now - self._last_anchor_render_time < 0.05:
            return
        self._last_anchor_render_time = now
        self.reload_overlay()
        if callable(self.on_change):
            self.on_change()

    def recent_motion_items(self) -> list[dict[str, Any]]:
        items = read_recent_motions()
        labels = recent_entry_labels(items)
        return [
            {
                "index": index,
                "label": labels[index],
                "motion_path": item.motion_path,
                "motion_id": item.motion_id,
                "contact_layer": item.contact_layer,
            }
            for index, item in enumerate(items)
        ]

    def open_recent_motion(self, index: int) -> None:
        items = read_recent_motions()
        if not items:
            raise ValueError("no recent motions")
        if index < 0 or index >= len(items):
            raise ValueError(f"recent motion index out of range: {index}")
        if not callable(self.reload_motion_callback):
            raise ValueError("in-process motion reload is unavailable")
        self.reload_motion_callback(items[index])

    def open_latest_motion(self) -> None:
        self.open_recent_motion(0)

    def reload_current_motion(self) -> None:
        if not callable(self.reload_motion_callback):
            raise ValueError("in-process motion reload is unavailable")
        self.reload_motion_callback(_recent_entry_from_session(self.state.session, terrain_urdf=self.terrain_urdf))


@dataclass
class _ShellState:
    last_message: str | None = "Load a motion bundle to start."
    last_error: str | None = None
    session: Any = None


@dataclass
class ContactEditorShellController:
    current: SurfaceEditorController | None = None
    state: _ShellState | SurfaceOverlayEditorState = field(default_factory=_ShellState)
    selected_anchor_id: str | None = None
    load_recent_callback: Any = None

    def set_current(self, controller: SurfaceEditorController) -> None:
        self.current = controller
        self.state = controller.state
        self.selected_anchor_id = controller.selected_anchor_id

    def graph(self) -> ContactGraph:
        if self.current is None:
            return ContactGraph(motion_id="not_loaded")
        return self.current.graph()

    def _anchor_obj(self, anchor_id: str | None = None) -> dict[str, Any] | None:
        return self.current._anchor_obj(anchor_id) if self.current is not None else None

    def pending_edits(self) -> list[ContactAnchorEditRecord]:
        return self.current.pending_edits() if self.current is not None else []

    def recent_motion_items(self) -> list[dict[str, Any]]:
        if self.current is not None:
            return self.current.recent_motion_items()
        items = read_recent_motions()
        labels = recent_entry_labels(items)
        return [
            {
                "index": index,
                "label": labels[index],
                "motion_path": item.motion_path,
                "motion_id": item.motion_id,
                "contact_layer": item.contact_layer,
            }
            for index, item in enumerate(items)
        ]

    def select_anchor(self, anchor_id: str | None) -> str | None:
        if self.current is None:
            self.state.last_error = "load a motion before selecting anchors"
            return None
        result = self.current.select_anchor(anchor_id)
        self.state = self.current.state
        self.selected_anchor_id = self.current.selected_anchor_id
        return result

    def save(self) -> Path | None:
        if self.current is None:
            self.state.last_error = "load a motion before saving"
            return None
        result = self.current.save()
        self.state = self.current.state
        return result

    def discard(self) -> None:
        if self.current is None:
            self.state.last_error = "load a motion before discarding"
            return
        self.current.discard()
        self.state = self.current.state

    def open_recent_motion(self, index: int) -> None:
        if self.current is None:
            items = read_recent_motions()
            if index < 0 or index >= len(items):
                self.state.last_error = f"recent motion index out of range: {index}"
                return
            if callable(self.load_recent_callback):
                self.load_recent_callback(items[index])
                if self.current is not None:
                    self.state = self.current.state
                    self.selected_anchor_id = self.current.selected_anchor_id
                return
            self.state.last_error = "load a motion before switching recent motions"
            return
        self.current.open_recent_motion(index)
        self.state = self.current.state
        self.selected_anchor_id = self.current.selected_anchor_id

    def open_latest_motion(self) -> None:
        self.open_recent_motion(0)

    def reload_current_motion(self) -> None:
        if self.current is None:
            self.state.last_error = "load a motion before reloading"
            return
        self.current.reload_current_motion()
        self.state = self.current.state
        self.selected_anchor_id = self.current.selected_anchor_id


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


def _session_plan_summary(session: SurfaceEditorSession) -> str:
    lines = [
        f"edit_plan: {session.edit_plan_path or '-'}",
        f"pending_edits: {len(read_pending_surface_edits(session))}",
        f"debug_contact_layer: {session.output_contact_layer or '-'}",
    ]
    if session.edit_plan_path:
        path = Path(session.edit_plan_path).expanduser()
        if path.exists():
            try:
                plan = read_contact_edit_plan(path)
                lines.extend([f"plan_status: {plan.status}", f"plan_edits: {len(plan.edits)}"])
            except Exception as exc:
                lines.append(f"plan_error: {exc}")
        else:
            lines.append("plan_status: not written")
    return "\n".join(lines)


def _write_session_edits_to_plan(session: SurfaceEditorSession) -> Path:
    if not session.edit_plan_path:
        raise ValueError("edit_plan is not configured for this session")
    plan_path = Path(session.edit_plan_path).expanduser()
    if plan_path.exists():
        plan = read_contact_edit_plan(plan_path)
    else:
        plan = ContactEditPlan(
            plan_id=plan_path.stem,
            source_motion_path=session.motion_path,
            source_motion_id=session.motion_id,
            source_contact_layer=session.contact_layer,
        )
    existing_edits = list(plan.edits)
    edit_index = {str(edit.get("edit_id")): index for index, edit in enumerate(existing_edits) if edit.get("edit_id")}
    for edit in coalesce_pending_surface_edits(session):
        metadata = dict(edit.metadata)
        metadata.update(
            {
                "session_name": session.session_name,
                "overlay_path": str(session.overlay_path),
                "report_path": str(session.report_path),
                "binding_granularity": "anchor_point",
            }
        )
        enriched = replace(edit, source="viser_surface_editor", metadata=metadata)
        edit_dict = enriched.to_dict()
        edit_id = str(edit_dict["edit_id"])
        if edit_id in edit_index:
            existing_edits[edit_index[edit_id]] = edit_dict
        else:
            edit_index[edit_id] = len(existing_edits)
            existing_edits.append(edit_dict)
    updated = ContactEditPlan(
        plan_id=plan.plan_id,
        source_motion_path=plan.source_motion_path or session.motion_path,
        source_motion_id=plan.source_motion_id or session.motion_id,
        source_contact_layer=plan.source_contact_layer or session.contact_layer,
        source_segment_layer=plan.source_segment_layer,
        edits=existing_edits,
        status="draft" if plan.status == "validated" else plan.status,
        output_motion_path=plan.output_motion_path,
        output_contact_layer=plan.output_contact_layer,
        output_segment_layer=plan.output_segment_layer,
        metadata=dict(plan.metadata),
    )
    write_contact_edit_plan(plan_path, updated)
    return plan_path


def _validate_session_plan(session: SurfaceEditorSession, *, layers_root: Path = LAYERS_ROOT) -> tuple[Path, list[str]]:
    _ = layers_root
    plan_path = _write_session_edits_to_plan(session)
    plan = read_contact_edit_plan(plan_path)
    warnings = validate_contact_edit_plan(plan)
    if plan.status == "draft":
        plan = replace(plan, status="validated")
    write_contact_edit_plan(plan_path, plan)
    return plan_path, warnings


def _save_and_validate_plan(session: SurfaceEditorSession, *, layers_root: Path = LAYERS_ROOT) -> tuple[Path | None, list[str]]:
    out = save_surface_editor_session(session, layers_root=layers_root)
    plan_path = Path(session.edit_plan_path).expanduser() if session.edit_plan_path else None
    if plan_path is None:
        raise ValueError("edit_plan is not configured for this session")
    plan = read_contact_edit_plan(plan_path)
    warnings = validate_contact_edit_plan(plan)
    if plan.status == "draft":
        plan = replace(plan, status="validated")
    write_contact_edit_plan(plan_path, plan)
    return out, warnings


def _default_generation_outputs(session: SurfaceEditorSession) -> dict[str, str]:
    stem = _safe_name(session.session_name or session.motion_id)
    return {
        "output_motion": str(Path("data/motions/generated") / f"{stem}_augmented.npz"),
        "output_motion_version_id": f"{stem}_augmented",
        "output_contact_layer": f"contact/{stem}_augmented",
        "output_segment_layer": f"candidates/{stem}_augmented",
        "intermediate_dir": str(Path("data/workbench/lte_intermediates") / stem),
    }


def _next_available_motion_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix or ".npz"
    for index in range(1, 10000):
        numbered = candidate.with_name(f"{stem}_{index:03d}{suffix}")
        if not numbered.exists():
            return numbered
    raise RuntimeError(f"could not find an available output path near {candidate}")


def _avoid_generation_output_collision(inputs: dict[str, Any]) -> dict[str, Any]:
    original_motion = Path(str(inputs["generated_motion"])).expanduser()
    available_motion = _next_available_motion_path(original_motion)
    if available_motion == original_motion:
        return inputs

    updated = dict(inputs)
    original_stem = original_motion.stem
    available_stem = available_motion.stem
    updated["generated_motion"] = str(available_motion)

    if not updated.get("generated_motion_version_id") or updated["generated_motion_version_id"] == original_stem:
        updated["generated_motion_version_id"] = available_stem
    if not updated.get("generated_contact_layer") or updated["generated_contact_layer"] == f"contact/{original_stem}":
        updated["generated_contact_layer"] = f"contact/{available_stem}"
    if not updated.get("generated_segment_layer") or updated["generated_segment_layer"] == f"candidates/{original_stem}":
        updated["generated_segment_layer"] = f"candidates/{available_stem}"

    intermediate = updated.get("intermediate_dir")
    if intermediate:
        intermediate_path = Path(str(intermediate)).expanduser()
        if intermediate_path.exists():
            updated["intermediate_dir"] = str(intermediate_path.with_name(available_stem))

    return updated


def _generate_fullbody_lte_from_session(
    session: SurfaceEditorSession,
    *,
    output_motion: str,
    output_motion_version_id: str | None = None,
    output_contact_layer: str | None = None,
    output_segment_layer: str | None = None,
    intermediate_dir: str | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
    register_motion_version: bool = False,
    lte_repo_root: str = "/home/xiaz/lte",
    ik_conda_env: str = "env_pyroki_climb_projection",
    layers_root: Path = LAYERS_ROOT,
) -> Any:
    plan_path, _warnings = _validate_session_plan(session, layers_root=layers_root)
    plan = read_contact_edit_plan(plan_path)
    return apply_contact_edit_plan_to_motion(
        plan,
        output_motion_path=output_motion,
        mode="lte_fullbody",
        source_plan_path=plan_path,
        output_contact_layer=output_contact_layer,
        output_segment_layer=output_segment_layer,
        output_motion_version_id=output_motion_version_id,
        overwrite=overwrite,
        dry_run=dry_run,
        register_motion_version=register_motion_version,
        lte_repo_root=lte_repo_root,
        ik_conda_env=ik_conda_env,
        intermediate_dir=intermediate_dir,
        layers_root=layers_root,
    )


def _open_file_dialog(*, title: str, filetypes: list[tuple[str, str]], initialdir: str | Path | None = None) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError(f"system file picker is unavailable: {exc}") from exc
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=str(Path(initialdir).expanduser()) if initialdir else None,
        )
        return selected or None
    finally:
        root.destroy()


def _save_file_dialog(*, title: str, defaultextension: str = "", filetypes: list[tuple[str, str]] | None = None, initialdir: str | Path | None = None) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError(f"system file picker is unavailable: {exc}") from exc
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.asksaveasfilename(
            title=title,
            defaultextension=defaultextension,
            filetypes=filetypes or [("All files", "*")],
            initialdir=str(Path(initialdir).expanduser()) if initialdir else None,
        )
        return selected or None
    finally:
        root.destroy()


SETUP_LOAD_TYPES = ("Motion", "Motion NPZ", "Contact Layer", "Terrain URDF", "Surface Catalog")
SETUP_SAVE_TYPES = ("Output Contact Layer", "Edit Plan")
PICKER_NONE = "<none>"


def _setup_load_dialog_config(load_type: str) -> dict[str, Any]:
    if load_type == "Motion":
        return {
            "title": "Load registered motion",
            "filetypes": [("Motion asset", "*.json")],
            "initialdir": MOTIONS_ROOT,
        }
    if load_type == "Motion NPZ":
        return {
            "title": "Load motion npz",
            "filetypes": [("Motion npz", "*.npz")],
            "initialdir": Path.cwd(),
        }
    if load_type == "Contact Layer":
        return {
            "title": "Load contact layer jsonl",
            "filetypes": [("Contact layer jsonl", "*.jsonl")],
            "initialdir": LAYERS_ROOT / "contact",
        }
    if load_type == "Terrain URDF":
        return {
            "title": "Load terrain URDF",
            "filetypes": [("URDF", "*.urdf")],
            "initialdir": Path.cwd(),
        }
    if load_type == "Surface Catalog":
        return {
            "title": "Load surface catalog",
            "filetypes": [("Surface catalog jsonl", "*.jsonl")],
            "initialdir": Path("data/surfaces"),
        }
    raise ValueError(f"unknown load type: {load_type}")


def _setup_load_suffixes(load_type: str) -> tuple[str, ...]:
    if load_type == "Motion":
        return (".json",)
    if load_type == "Motion NPZ":
        return (".npz",)
    if load_type == "Contact Layer":
        return (".jsonl",)
    if load_type == "Terrain URDF":
        return (".urdf",)
    if load_type == "Surface Catalog":
        return (".jsonl",)
    raise ValueError(f"unknown load type: {load_type}")


def _setup_load_roots(load_type: str) -> list[Path]:
    repo = Path.cwd()
    candidates: list[Path]
    if load_type == "Motion":
        candidates = [MOTIONS_ROOT]
    elif load_type == "Motion NPZ":
        candidates = [
            repo,
            repo / "data",
            Path("/home/xiaz/holosoma_isaaclab3_newton/tmp"),
            Path("/home/xiaz/holosoma_isaaclab3_newton/OmniRetarget_Dataset/data"),
        ]
    elif load_type == "Contact Layer":
        candidates = [LAYERS_ROOT / "contact"]
    elif load_type == "Terrain URDF":
        candidates = [
            repo,
            Path("/home/xiaz/holosoma_isaaclab3_newton/OmniRetarget_Dataset/models/terrain"),
        ]
    elif load_type == "Surface Catalog":
        candidates = [repo / "data" / "surfaces"]
    else:
        raise ValueError(f"unknown load type: {load_type}")
    seen: set[Path] = set()
    roots: list[Path] = []
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def _matches_suffix(path: Path, suffixes: tuple[str, ...]) -> bool:
    return path.is_file() and path.suffix.lower() in suffixes


def _directory_contains_loadable_file(path: Path, suffixes: tuple[str, ...]) -> bool:
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [item for item in dirs if not item.startswith(".") and item != "__pycache__"]
            if any(Path(name).suffix.lower() in suffixes for name in files):
                return True
    except OSError:
        return False
    return False


def _filtered_picker_entries(current_dir: str | Path, suffixes: tuple[str, ...]) -> list[tuple[str, Path]]:
    directory = Path(current_dir).expanduser()
    try:
        children = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return []
    entries: list[tuple[str, Path]] = []
    for child in children:
        if child.name.startswith("."):
            continue
        if child.is_dir():
            if _directory_contains_loadable_file(child, suffixes):
                entries.append((f"[dir] {child.name}", child))
        elif _matches_suffix(child, suffixes):
            entries.append((f"[file] {child.name}", child))
    return entries


def _filtered_open_file_dialog(*, title: str, load_type: str) -> str | None:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        raise RuntimeError(f"filtered file picker is unavailable: {exc}") from exc

    suffixes = _setup_load_suffixes(load_type)
    roots = [
        root for root in _setup_load_roots(load_type)
        if _directory_contains_loadable_file(root, suffixes)
    ]
    if not roots:
        return None

    state: dict[str, Any] = {
        "current_dir": roots[0],
        "entries": [],
        "selected": None,
    }

    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    root.geometry("760x520")

    selected_root = tk.StringVar(value=str(roots[0]))
    current_dir_text = tk.StringVar(value=str(roots[0]))
    status_text = tk.StringVar(value=f"{load_type}: only folders containing loadable files are shown")

    main = ttk.Frame(root, padding=8)
    main.pack(fill=tk.BOTH, expand=True)
    ttk.Label(main, text=load_type).pack(anchor=tk.W)
    root_combo = ttk.Combobox(main, textvariable=selected_root, values=[str(path) for path in roots], state="readonly")
    root_combo.pack(fill=tk.X, pady=(2, 8))
    ttk.Label(main, textvariable=current_dir_text).pack(anchor=tk.W)
    listbox = tk.Listbox(main, height=18)
    scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=listbox.yview)
    listbox.configure(yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
    scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=8)

    button_frame = ttk.Frame(root, padding=(8, 0, 8, 8))
    button_frame.pack(fill=tk.X)
    open_button = ttk.Button(button_frame, text="Open selected")
    open_button.pack(side=tk.LEFT)
    up_button = ttk.Button(button_frame, text="Up")
    up_button.pack(side=tk.LEFT, padx=(8, 0))
    cancel_button = ttk.Button(button_frame, text="Cancel")
    cancel_button.pack(side=tk.RIGHT)
    ttk.Label(root, textvariable=status_text, padding=(8, 0, 8, 8)).pack(anchor=tk.W)

    def refresh_entries() -> None:
        directory = Path(state["current_dir"]).expanduser().resolve()
        state["entries"] = _filtered_picker_entries(directory, suffixes)
        current_dir_text.set(str(directory))
        listbox.delete(0, tk.END)
        if not state["entries"]:
            listbox.insert(tk.END, PICKER_NONE)
            status_text.set(f"{load_type}: no loadable files in this branch")
            return
        for label, _path in state["entries"]:
            listbox.insert(tk.END, label)
        listbox.selection_set(0)
        status_text.set(f"{load_type}: {len(state['entries'])} loadable entries")

    def open_selected() -> None:
        selection = listbox.curselection()
        if not selection or not state["entries"]:
            return
        _label, path = state["entries"][selection[0]]
        if path.is_dir():
            state["current_dir"] = path
            refresh_entries()
            return
        state["selected"] = str(path)
        root.quit()

    def move_up() -> None:
        current = Path(state["current_dir"]).expanduser().resolve()
        parent = current.parent
        if parent == current or not _directory_contains_loadable_file(parent, suffixes):
            status_text.set(f"Parent has no loadable {load_type} files")
            return
        state["current_dir"] = parent
        refresh_entries()

    def change_root(_event: Any = None) -> None:
        state["current_dir"] = Path(selected_root.get())
        refresh_entries()

    root_combo.bind("<<ComboboxSelected>>", change_root)
    listbox.bind("<Double-Button-1>", lambda _event: open_selected())
    listbox.bind("<Return>", lambda _event: open_selected())
    open_button.configure(command=open_selected)
    up_button.configure(command=move_up)
    cancel_button.configure(command=root.quit)

    refresh_entries()
    try:
        root.mainloop()
        return state["selected"]
    finally:
        root.destroy()


def _setup_save_dialog_config(save_type: str) -> dict[str, Any]:
    if save_type == "Output Contact Layer":
        return {
            "title": "Save contact layer as jsonl",
            "defaultextension": ".jsonl",
            "filetypes": [("Contact layer jsonl", "*.jsonl")],
            "initialdir": LAYERS_ROOT / "contact",
        }
    if save_type == "Edit Plan":
        return {
            "title": "Save edit plan as JSON",
            "defaultextension": ".json",
            "filetypes": [("Contact edit plan", "*.json")],
            "initialdir": WORKBENCH_ROOT,
        }
    raise ValueError(f"unknown save type: {save_type}")


def _layer_name_from_path(path: str | Path) -> str:
    resolved = Path(path).expanduser()
    try:
        rel = resolved.resolve().relative_to(LAYERS_ROOT.resolve())
    except ValueError:
        return str(resolved)
    if rel.suffix == ".jsonl":
        rel = rel.parent
    return rel.as_posix()


def _contact_editor_config_from_motion_asset(path: str | Path) -> ContactEditorConfig:
    selected_path = Path(path).expanduser()
    record = read_motion_asset(selected_path.stem, selected_path)
    derived = record.derived or {}
    source_contact_layer = derived.get("bound_contact_layer") or derived.get("contact_layer")
    if not source_contact_layer:
        raise ValueError(f"motion has no derived contact layer: {record.motion_asset_id}")
    return ContactEditorConfig(
        motion=record.motion_path,
        motion_id=record.motion_id or record.motion_asset_id,
        source_contact_layer=source_contact_layer,
        session_name=f"{record.motion_asset_id}_contact_editor",
        surface_catalog=record.surface_catalog_path,
        terrain_urdf=record.terrain_urdf,
        output_prefix=f"contact/{record.motion_asset_id}_contact_editor",
        edit_plan=derived.get("edit_plan_path"),
        output_contact_layer=derived.get("output_contact_layer"),
        repo_root=None,
        with_terrain=bool(record.terrain_urdf),
        fps=int(record.fps or 50),
    )


def _recent_entry_from_motion_asset(path: str | Path) -> RecentMotionEntry:
    selected_path = Path(path).expanduser()
    record = read_motion_asset(selected_path.stem, selected_path)
    derived = record.derived or {}
    return RecentMotionEntry(
        label=record.motion_asset_id,
        motion_asset_path=str(selected_path),
        motion_path=record.motion_path,
        motion_id=record.motion_id or record.motion_asset_id,
        terrain_urdf=record.terrain_urdf,
        contact_layer=derived.get("bound_contact_layer") or derived.get("contact_layer"),
        surface_catalog=record.surface_catalog_path,
        edit_plan_path=derived.get("edit_plan_path"),
        output_contact_layer=derived.get("output_contact_layer"),
        metadata={"source": "motion_asset"},
    )


def _contact_editor_config_from_recent_entry(entry: RecentMotionEntry) -> ContactEditorConfig:
    if entry.motion_asset_path:
        try:
            return _contact_editor_config_from_motion_asset(entry.motion_asset_path)
        except Exception:
            pass
    if not entry.contact_layer:
        raise ValueError(f"recent motion has no contact layer: {entry.label}")
    return ContactEditorConfig(
        motion=entry.motion_path,
        motion_id=entry.motion_id,
        source_contact_layer=entry.contact_layer,
        session_name=f"{_safe_name(entry.label or entry.motion_id)}_contact_editor",
        surface_catalog=entry.surface_catalog,
        terrain_urdf=entry.terrain_urdf,
        output_prefix=f"contact/{_safe_name(entry.label or entry.motion_id)}_contact_editor",
        edit_plan=entry.edit_plan_path,
        output_contact_layer=entry.output_contact_layer,
        repo_root=None,
        with_terrain=bool(entry.terrain_urdf),
    )


def _recent_entry_from_session(
    session: SurfaceEditorSession,
    *,
    label: str | None = None,
    terrain_urdf: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> RecentMotionEntry:
    return RecentMotionEntry(
        label=label or Path(session.motion_path).stem,
        motion_path=session.motion_path,
        motion_id=session.motion_id,
        terrain_urdf=terrain_urdf,
        contact_layer=session.contact_layer,
        surface_catalog=session.surface_catalog,
        edit_plan_path=session.edit_plan_path,
        output_contact_layer=session.output_contact_layer,
        metadata=metadata or {},
    )


def _recent_entry_from_generated_session(
    session: SurfaceEditorSession,
    *,
    output_motion: str,
    output_contact_layer: str | None,
    output_segment_layer: str | None,
    output_motion_version_id: str | None,
    terrain_urdf: str | None = None,
) -> RecentMotionEntry:
    label = output_motion_version_id or Path(output_motion).stem
    return RecentMotionEntry(
        label=label,
        motion_path=output_motion,
        motion_id=session.motion_id,
        terrain_urdf=terrain_urdf,
        contact_layer=output_contact_layer,
        surface_catalog=session.surface_catalog,
        edit_plan_path=session.edit_plan_path,
        output_contact_layer=output_contact_layer,
        metadata={
            "kind": "lte_augmented",
            "parent_motion_path": session.motion_path,
            "output_segment_layer": output_segment_layer,
        },
    )


def _loaded_editor_command_from_config(
    config: ContactEditorConfig,
    *,
    timeline_port: int,
    edit_mode: str,
    default_mode: str,
    show_only: str,
    fps: int,
    robot_urdf: str | Path | None = None,
) -> tuple[list[str], Any]:
    prepared = prepare_contact_editor_workbench_session(config)
    terrain_urdf_for_viewer = infer_terrain_urdf(config)
    repo_path = Path(config.repo_root).expanduser() if config.repo_root else Path("/home/xiaz/holosoma_isaaclab3_newton")
    resolved_robot_urdf = Path(robot_urdf).expanduser() if robot_urdf else repo_path / "OmniRetarget_Dataset/models/g1/g1_29dof_spherehand.urdf"
    cmd = [
        sys.executable,
        "-m",
            "motion_edit.viewer.contact_editor.app",
        "--qpos-npz",
        str(Path(config.motion).expanduser().resolve()),
        "--surface-binding-overlay",
        str(prepared.session.overlay_path),
        "--surface-editor-session",
        str(prepared.session.session_dir / "session.json"),
        "--surface-editor-requests",
        str(prepared.session.request_path),
        "--edit-mode",
        str(edit_mode),
        "--default-mode",
        str(default_mode),
        "--show-only",
        str(show_only),
        "--timeline-port",
        str(timeline_port),
        "--fps",
        str(fps or config.fps),
    ]
    object_urdf = config.terrain_urdf or terrain_urdf_for_viewer
    if object_urdf and config.with_terrain:
        cmd.extend(["--object-urdf", str(object_urdf), "--with-terrain"])
    if resolved_robot_urdf.exists():
        cmd.extend(["--robot-urdf", str(resolved_robot_urdf)])
    return cmd, prepared


def _prepared_state_from_config(config: ContactEditorConfig) -> tuple[SurfaceOverlayEditorState, Any, str | None]:
    prepared = prepare_contact_editor_workbench_session(config)
    state = load_editor_state(prepared.session.session_dir / "session.json")
    terrain_urdf_for_viewer = infer_terrain_urdf(config)
    return state, prepared, terrain_urdf_for_viewer


def _exec_loaded_editor_from_motion_asset(
    motion_asset_path: str | Path,
    *,
    timeline_port: int,
    edit_mode: str,
    default_mode: str,
    show_only: str,
    fps: int,
    robot_urdf: str | Path | None = None,
) -> None:
    config = _contact_editor_config_from_motion_asset(motion_asset_path)
    cmd, prepared = _loaded_editor_command_from_config(
        config,
        timeline_port=timeline_port,
        edit_mode=edit_mode,
        default_mode=default_mode,
        show_only=show_only,
        fps=fps,
        robot_urdf=robot_urdf,
    )
    print(
        "[surface editor] loaded motion asset "
        f"{Path(motion_asset_path).name}: anchors={prepared.ready_anchor_count} "
        f"session={prepared.session.session_dir}"
    )
    print(f"[surface editor] exec: {' '.join(cmd)}")
    os.execv(sys.executable, cmd)


def _exec_loaded_editor_from_recent_entry(
    entry: RecentMotionEntry,
    *,
    timeline_port: int,
    edit_mode: str,
    default_mode: str,
    show_only: str,
    fps: int,
    robot_urdf: str | Path | None = None,
) -> None:
    config = _contact_editor_config_from_recent_entry(entry)
    cmd, prepared = _loaded_editor_command_from_config(
        config,
        timeline_port=timeline_port,
        edit_mode=edit_mode,
        default_mode=default_mode,
        show_only=show_only,
        fps=fps,
        robot_urdf=robot_urdf,
    )
    upsert_recent_motion(entry)
    print(
        "[surface editor] loaded recent motion "
        f"{entry.label}: anchors={prepared.ready_anchor_count} session={prepared.session.session_dir}"
    )
    print(f"[surface editor] exec: {' '.join(cmd)}")
    os.execv(sys.executable, cmd)


def _add_loaded_editor_sidebar(
    server: Any,
    *,
    controller: SurfaceEditorController,
    args: argparse.Namespace,
    playback: MotionPlaybackController | None,
) -> None:
    status_refs: dict[str, Any] = {}
    generation_state = GenerationJobState()

    def _current_frame_text() -> str:
        if playback is None:
            return "no playback"
        return f"{playback.frame()} / {max(0, playback.n_frames - 1)}"

    def _set_status(text: str) -> None:
        controller.state.last_message = text
        widget = status_refs.get("status")
        if widget is not None:
            widget.value = text
        print(f"[surface editor] {text}")

    def _refresh_info() -> None:
        motion_widget = status_refs.get("current_motion")
        session_widget = status_refs.get("current_session")
        selected = status_refs.get("selected_anchor")
        info = status_refs.get("anchor_info")
        frame = status_refs.get("frame")
        if motion_widget is not None:
            motion_widget.value = str(controller.state.session.motion_path)
        if session_widget is not None:
            session_widget.value = str(controller.state.session.session_dir / "session.json")
        if selected is not None:
            selected.value = controller.selected_anchor_id or ""
        if info is not None:
            info.value = controller.selected_info_text()
        if frame is not None:
            frame.value = _current_frame_text()
        plan_info = status_refs.get("plan_info")
        if plan_info is not None:
            plan_info.value = _session_plan_summary(controller.state.session)
        status = status_refs.get("status")
        if status is not None:
            status.value = controller.state.last_error or controller.state.last_message or "ready"
        generation_info = status_refs.get("generation_info")
        if generation_info is not None:
            if generation_state.running:
                generation_info.value = f"running: {generation_state.last_output_motion or ''}"
            elif generation_state.last_error:
                generation_info.value = f"failed: {generation_state.last_error}"
            elif generation_state.last_output_motion:
                generation_info.value = f"last output: {generation_state.last_output_motion}"
            else:
                generation_info.value = "idle"

    with server.gui.add_folder("Contact Anchor"):
        show_all_anchors = server.gui.add_checkbox("show all anchors", initial_value=controller.show_all_anchors)
        selected_anchor = server.gui.add_text("anchor_id", initial_value=controller.selected_anchor_id or "")
        selected_anchor.disabled = True
        anchor_info = server.gui.add_text("info", initial_value=controller.selected_info_text(), multiline=True)
        anchor_info.disabled = True
    status_refs["selected_anchor"] = selected_anchor
    status_refs["anchor_info"] = anchor_info

    @show_all_anchors.on_update
    def _(_) -> None:
        controller.show_all_anchors = bool(show_all_anchors.value)
        controller.reload_overlay()
        _set_status("showing all anchors" if controller.show_all_anchors else "showing anchors active at current frame")
        _refresh_info()

    defaults = _default_generation_outputs(controller.state.session)
    with server.gui.add_folder("Advanced / Generate"):
        output_motion = server.gui.add_text("output_motion", initial_value=defaults["output_motion"])
        overwrite = server.gui.add_checkbox("overwrite output", initial_value=False)
        generate_btn = server.gui.add_button("Generate fullbody LTE")
        generation_info = server.gui.add_text("generation_status", initial_value="idle", multiline=True)
        generation_info.disabled = True
    status_refs["generation_info"] = generation_info

    def _generation_inputs() -> dict[str, Any]:
        generated_motion = str(output_motion.value).strip()
        if not generated_motion:
            raise ValueError("output_motion is required")
        return {
            "generated_motion": generated_motion,
            "generated_contact_layer": defaults["output_contact_layer"],
            "generated_segment_layer": defaults["output_segment_layer"],
            "generated_motion_version_id": defaults["output_motion_version_id"],
            "intermediate_dir": defaults["intermediate_dir"],
            "overwrite": bool(overwrite.value),
            "register_motion_version": False,
        }

    def _run_generation(*, dry_run: bool, inputs: dict[str, Any]) -> None:
        result = _generate_fullbody_lte_from_session(
            controller.state.session,
            output_motion=inputs["generated_motion"],
            output_motion_version_id=inputs["generated_motion_version_id"],
            output_contact_layer=inputs["generated_contact_layer"],
            output_segment_layer=inputs["generated_segment_layer"],
            intermediate_dir=inputs["intermediate_dir"],
            dry_run=dry_run,
            overwrite=inputs["overwrite"],
            register_motion_version=inputs["register_motion_version"],
        )
        if not dry_run:
            generated_entry = _recent_entry_from_generated_session(
                controller.state.session,
                output_motion=str(result.output_motion_path),
                output_contact_layer=inputs["generated_contact_layer"],
                output_segment_layer=inputs["generated_segment_layer"],
                output_motion_version_id=inputs["generated_motion_version_id"],
                terrain_urdf=controller.terrain_urdf,
            )
            upsert_recent_motion(generated_entry)
            if callable(controller.reload_motion_callback):
                controller.reload_motion_callback(generated_entry)
        action = "dry-run fullbody LTE" if dry_run else "generated fullbody LTE"
        warning_suffix = f" warnings={len(result.warnings or [])}" if result.warnings else ""
        _set_status(f"{action}: {result.output_motion_path}{warning_suffix}")
        generation_state.last_output_motion = str(result.output_motion_path)
        generation_state.last_error = None

    def _start_generation(*, dry_run: bool) -> None:
        if generation_state.running:
            controller.state.last_error = "generation already running"
            print("[surface editor] generation already running")
            _refresh_info()
            return
        try:
            inputs = _generation_inputs()
        except Exception as exc:
            controller.state.last_error = str(exc)
            print(f"[surface editor] generation setup failed: {exc}")
            _refresh_info()
            return
        if not dry_run and not inputs["overwrite"]:
            resolved_inputs = _avoid_generation_output_collision(inputs)
            if resolved_inputs != inputs:
                inputs = resolved_inputs
                output_motion.value = inputs["generated_motion"]
                _set_status(f"output existed; using next available motion: {inputs['generated_motion']}")
        action = "dry-run fullbody LTE" if dry_run else "generate fullbody LTE"
        generation_state.running = True
        generation_state.last_error = None
        generation_state.last_output_motion = inputs["generated_motion"]
        generation_state.last_started_at = time.time()
        controller.state.last_error = None
        _set_status(f"{action} started: {inputs['generated_motion']}")
        _refresh_info()

        def _worker() -> None:
            try:
                print(
                    "[surface editor] "
                    f"{action} worker started output={inputs['generated_motion']} "
                    f"plan={controller.state.session.edit_plan_path}"
                )
                _run_generation(dry_run=dry_run, inputs=inputs)
                print(f"[surface editor] {action} worker finished output={inputs['generated_motion']}")
            except Exception as exc:
                generation_state.last_error = str(exc)
                controller.state.last_error = f"{action} failed: {exc}"
                print(f"[surface editor] {action} failed: {exc}")
            finally:
                generation_state.running = False
                generation_state.last_finished_at = time.time()
                _refresh_info()

        threading.Thread(target=_worker, daemon=True).start()

    @generate_btn.on_click
    def _(_) -> None:
        _start_generation(dry_run=False)

    previous_on_change = controller.on_change

    def _on_change() -> None:
        if callable(previous_on_change):
            previous_on_change()
        _refresh_info()

    controller.on_change = _on_change
    _refresh_info()


def _safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in text)


def _color(status: str | None) -> tuple[int, int, int]:
    return STATUS_COLORS.get(str(status or ""), (80, 180, 255))


def _anchor_color(obj: dict[str, Any]) -> tuple[int, int, int]:
    status = str(obj.get("status", ""))
    if status in STATUS_COLOR_OVERRIDES:
        return _color(status)
    role = str(obj.get("patch_role") or "").lower()
    if role in FOOT_PATCH_ROLE_COLORS:
        return FOOT_PATCH_ROLE_COLORS[role]
    explicit = obj.get("color")
    if isinstance(explicit, list) and len(explicit) == 3:
        return tuple(int(value) for value in explicit)
    body = str(obj.get("body", "")).lower()
    for key, color in BODY_COLORS.items():
        if key in body or body in key:
            return color
    return _color(status)


def _anchor_patch_radius(record: ContactAnchorRecord) -> float:
    role = str(record.metadata.get("patch_role") or "").lower()
    return FOOT_PATCH_ROLE_RADII.get(role, 0.045)


def _remove_handles(handles: list[Any]) -> None:
    for handle in handles:
        remove = getattr(handle, "remove", None)
        if callable(remove):
            remove()


def _anchor_patch_mesh(
    record: ContactAnchorRecord,
    *,
    radius: float | None = None,
    normal_offset: float = 0.002,
    segments: int = 24,
) -> tuple[np.ndarray, np.ndarray] | None:
    if record.world_position is None or record.surface_tangent_u is None or record.surface_tangent_v is None:
        return None
    radius = _anchor_patch_radius(record) if radius is None else radius
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
            if controller is not None and not controller.should_render_anchor(anchor_id, obj):
                continue
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

                @marker.on_drag
                def _(event: Any, anchor_id: str = anchor_id) -> None:
                    if edit_mode != "direct":
                        controller.state.last_message = "drag disabled in request mode"
                        return
                    if event.phase == "start" and controller.selected_anchor_id != anchor_id:
                        controller.select_anchor(anchor_id)
                    record = controller._anchor_record(anchor_id)
                    if record is None:
                        return
                    try:
                        projected = controller.projected_world_request(record, event.end_position)
                        if event.phase == "update":
                            event.target.position = tuple(float(v) for v in projected)
                            return
                        if event.phase == "end":
                            mode = str(controller.drag_mode_getter()) if callable(controller.drag_mode_getter) else "reject"
                            result = controller.drag_selected_to_world(event.end_position, mode=mode)
                            print(f"[surface editor] dragged anchor={anchor_id} result={result}")
                            if callable(controller.on_change):
                                controller.on_change()
                    except Exception as exc:
                        controller.state.last_error = str(exc)
                        if event.phase == "end" and callable(controller.on_change):
                            controller.on_change()

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


def _add_motion_root_path(server: Any, qpos: np.ndarray) -> list[Any]:
    if qpos.shape[0] <= 1 or qpos.shape[1] < 3:
        return []
    motion_points = qpos[:, :3]
    handle = server.scene.add_line_segments(
        "/motion/root_path",
        points=np.stack([motion_points[:-1], motion_points[1:]], axis=1),
        colors=np.full((motion_points.shape[0] - 1, 2, 3), 160, dtype=np.uint8),
        line_width=1.5,
        visible=True,
    )
    return [handle]


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
    show_gui: bool = True,
) -> tuple[list[Any], MotionPlaybackController | None]:
    handles: list[Any] = []
    if object_urdf:
        object_path = Path(object_urdf)
        if object_path.exists():
            handles.extend(_add_static_urdf(server, root_name="/object", urdf_path=object_path))
    if robot_urdf is None or not Path(robot_urdf).exists():
        print("[surface editor] robot_urdf missing; showing root trace only")
        return handles, None
    try:
        import yourdfpy  # type: ignore[import-untyped]
        from viser.extras import ViserUrdf  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"[surface editor] robot playback unavailable: {exc}")
        return handles, None

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

    class _ValueBox:
        def __init__(self, value: Any) -> None:
            self.value = value

        def on_update(self, func: Any) -> Any:
            return func

    class _ButtonBox:
        def on_click(self, func: Any) -> Any:
            return func

    if show_gui:
        with server.gui.add_folder("Timeline"):
            frame_slider = server.gui.add_slider("frame", min=0, max=max(0, n_frames - 1), step=1, initial_value=0)
            frame_text = server.gui.add_text("current_frame", initial_value=f"0 / {max(0, n_frames - 1)}")
            play_btn = server.gui.add_button("Play / Pause")
            prev_btn = server.gui.add_button("Previous frame")
            next_btn = server.gui.add_button("Next frame")
            fps_in = server.gui.add_number("fps", initial_value=int(fps), min=1, max=240, step=1)
            loop_cb = server.gui.add_checkbox("loop", initial_value=True)
    else:
        frame_slider = _ValueBox(0)
        frame_text = _ValueBox(f"0 / {max(0, n_frames - 1)}")
        play_btn = _ButtonBox()
        prev_btn = _ButtonBox()
        next_btn = _ButtonBox()
        fps_in = _ValueBox(int(fps))
        loop_cb = _ValueBox(True)

    playback = MotionPlaybackController(
        n_frames=n_frames,
        current_frame=current_frame,
        playing=playing,
        apply_frame=_apply_frame,
        frame_slider=frame_slider,
        frame_text=frame_text,
        stop_callback=lambda: stop_flag.__setitem__("value", True),
    )

    @frame_slider.on_update
    def _(_) -> None:
        frame = int(np.clip(int(frame_slider.value), 0, max(0, n_frames - 1)))
        current_frame["value"] = float(frame)
        _apply_frame(frame)
        frame_text.value = f"{frame} / {max(0, n_frames - 1)}"
        if callable(playback.frame_change_callback):
            playback.frame_change_callback(frame)

    @play_btn.on_click
    def _(_) -> None:
        playback.toggle()

    @prev_btn.on_click
    def _(_) -> None:
        playback.step(-1)

    @next_btn.on_click
    def _(_) -> None:
        playback.step(1)

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
            frame_text.value = f"{frame} / {max(0, n_frames - 1)}"
            if callable(playback.frame_change_callback):
                playback.frame_change_callback(frame)
            time.sleep(0.01)

    _apply_frame(0)
    thread = threading.Thread(target=_play_loop, daemon=True)
    thread.start()
    return handles, playback


def run_surface_overlay_player(args: argparse.Namespace) -> None:
    try:
        import viser  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit("viser is not installed in this environment; use surface-editor fallback/sync commands") from exc
    if args.setup_mode:
        run_contact_editor_setup_player(args, viser)
        return
    if args.qpos_npz is None or args.surface_binding_overlay is None or args.surface_editor_session is None or args.surface_editor_requests is None:
        raise SystemExit("loaded surface editor requires --qpos-npz, --surface-binding-overlay, --surface-editor-session, and --surface-editor-requests")

    state = load_editor_state(args.surface_editor_session)
    overlay = load_surface_overlay(args.surface_binding_overlay)
    viewer_port = int(args.viser_port or args.timeline_port)
    shell_port = int(args.timeline_port + 1)
    _require_available_port(viewer_port, label="internal Viser")
    _require_available_port(shell_port, label="contact editor shell")
    server = viser.ViserServer(port=viewer_port)
    _assert_viser_port(server, viewer_port)
    server.gui.configure_theme(control_layout="fixed", control_width="large", dark_mode=True, show_logo=False, show_share_button=False)
    server.scene.add_grid("/grid", width=8.0, height=8.0, position=(0.0, 0.0, 0.0))

    playback_slot = ReloadablePlayback()
    motion_handles: list[Any] = []
    controller = SurfaceEditorController.create(server, state)
    controller.edit_mode = args.edit_mode
    controller.current_frame_getter = playback_slot.frame
    controller.timeline_port = shell_port
    controller.default_mode = str(args.default_mode)
    controller.show_only = str(args.show_only)
    controller.fps = int(args.fps or 50)
    controller.robot_urdf = args.robot_urdf
    controller.terrain_urdf = args.object_urdf if args.with_terrain else None

    start_contact_timeline_wrapper(
        controller=controller,
        playback=playback_slot,
        timeline_port=shell_port,
        viser_port=viewer_port,
        motion_name=Path(args.qpos_npz).name,
        fps=int(args.fps or 50),
    )

    def _replace_motion_visuals(
        *,
        motion_path: str | Path,
        object_urdf: str | Path | None,
        fps_hint: int,
    ) -> int:
        nonlocal motion_handles
        _remove_handles(motion_handles)
        motion_handles = []
        qpos, motion_fps = load_motion_sequence(motion_path)
        playback_handles, next_playback = _add_motion_playback(
            server,
            qpos=qpos,
            fps=int(fps_hint or motion_fps),
            robot_urdf=args.robot_urdf,
            object_urdf=object_urdf,
            show_gui=False,
        )
        motion_handles.extend(playback_handles)
        motion_handles.extend(_add_motion_root_path(server, qpos))
        next_playback.frame_change_callback = controller.on_frame_changed
        playback_slot.replace(next_playback)
        return int(fps_hint or motion_fps)

    motion_fps = _replace_motion_visuals(
        motion_path=args.qpos_npz,
        object_urdf=args.object_urdf if args.with_terrain else None,
        fps_hint=int(args.fps or 0),
    )
    controller.fps = int(args.fps or motion_fps)

    def _reload_entry_in_process(entry: RecentMotionEntry) -> None:
        config = _contact_editor_config_from_recent_entry(entry)
        next_state, prepared, terrain_urdf_for_viewer = _prepared_state_from_config(config)
        object_urdf = config.terrain_urdf or terrain_urdf_for_viewer
        next_fps = _replace_motion_visuals(
            motion_path=config.motion,
            object_urdf=object_urdf if config.with_terrain else None,
            fps_hint=int(args.fps or config.fps),
        )
        controller.state = next_state
        controller.original_graph = copy.deepcopy(read_surface_editor_graph(next_state.session))
        controller.undo_stack.clear()
        controller.redo_stack.clear()
        controller.terrain_urdf = object_urdf if config.with_terrain else None
        controller.fps = next_fps
        controller.selected_anchor_id = controller.default_anchor_id()
        controller.state.selected_anchor_id = controller.selected_anchor_id
        controller.state.last_message = f"loaded motion: {Path(config.motion).name}"
        controller.state.last_error = None
        controller.reload_overlay()
        upsert_recent_motion(entry)
        if callable(controller.on_change):
            controller.on_change()
        print(
            "[surface editor] reloaded motion in-place "
            f"{entry.label}: anchors={prepared.ready_anchor_count} session={prepared.session.session_dir}"
        )

    controller.reload_motion_callback = _reload_entry_in_process
    upsert_recent_motion(
        _recent_entry_from_session(
            state.session,
            label=Path(args.qpos_npz).stem,
            terrain_urdf=controller.terrain_urdf,
            metadata={"source": "loaded_editor"},
        )
    )
    if args.select_anchor:
        controller.select_anchor(args.select_anchor)
    anchor_ids = [str(anchor.get("anchor_id", "")) for anchor in controller.anchors() if anchor.get("anchor_id")]
    controller.on_change = lambda: None
    controller.drag_mode_getter = lambda: str(args.default_mode)

    controller.reload_overlay()
    _add_loaded_editor_sidebar(server, controller=controller, args=args, playback=playback_slot)

    print(f"[surface editor] overlay={args.surface_binding_overlay}")
    print(f"[surface editor] session={args.surface_editor_session}")
    print(f"[surface editor] requests={args.surface_editor_requests}")
    print(f"[surface editor] edit_mode={args.edit_mode}")
    print(f"[surface editor] robot_urdf={args.robot_urdf or 'none'}")
    print(f"[surface editor] object_urdf={args.object_urdf if args.with_terrain else 'none'}")
    print(f"[surface editor] Open Contact Editor: http://localhost:{shell_port}")
    if anchor_ids:
        print(f"[surface editor] anchors={', '.join(anchor_ids[:20])}{' ...' if len(anchor_ids) > 20 else ''}")
    print("Close this process with Ctrl+C.")
    while True:
        time.sleep(1.0)


def run_contact_editor_setup_player(args: argparse.Namespace, viser: Any) -> None:
    viewer_port = int(args.viser_port or args.timeline_port)
    shell_port = int(args.timeline_port + 1)
    _require_available_port(viewer_port, label="internal Viser")
    _require_available_port(shell_port, label="contact editor shell")
    server = viser.ViserServer(port=viewer_port)
    _assert_viser_port(server, viewer_port)
    server.gui.configure_theme(control_layout="fixed", control_width="large", dark_mode=True, show_logo=False, show_share_button=False)
    server.scene.add_grid("/grid", width=8.0, height=8.0, position=(0.0, 0.0, 0.0))
    playback_slot = ReloadablePlayback()
    motion_handles: list[Any] = []
    controller_box: dict[str, SurfaceEditorController | None] = {"controller": None}
    shell_controller = ContactEditorShellController()
    start_contact_timeline_wrapper(
        controller=shell_controller,
        playback=playback_slot,
        timeline_port=shell_port,
        viser_port=viewer_port,
        motion_name="not_loaded",
        fps=int(args.fps),
    )

    def _replace_motion_visuals(
        *,
        motion_path: str | Path,
        robot_urdf: str | Path | None,
        object_urdf: str | Path | None,
        fps_hint: int,
    ) -> int:
        nonlocal motion_handles
        _remove_handles(motion_handles)
        motion_handles = []
        qpos, motion_fps = load_motion_sequence(motion_path)
        playback_handles, next_playback = _add_motion_playback(
            server,
            qpos=qpos,
            fps=int(fps_hint or motion_fps),
            robot_urdf=robot_urdf,
            object_urdf=object_urdf,
            show_gui=False,
        )
        motion_handles.extend(playback_handles)
        motion_handles.extend(_add_motion_root_path(server, qpos))
        active_controller = controller_box.get("controller")
        if active_controller is not None:
            next_playback.frame_change_callback = active_controller.on_frame_changed
        playback_slot.replace(next_playback)
        return int(fps_hint or motion_fps)

    with server.gui.add_folder("Load"):
        load_type = server.gui.add_dropdown("load_type", options=SETUP_LOAD_TYPES, initial_value=SETUP_LOAD_TYPES[0])
        browse_btn = server.gui.add_button("Load selected type...")
        save_type = server.gui.add_dropdown("save_type", options=SETUP_SAVE_TYPES, initial_value=SETUP_SAVE_TYPES[0])
        save_as_btn = server.gui.add_button("Choose output...")

    with server.gui.add_folder("Motion Bundle"):
        motion = server.gui.add_text("motion_npz", initial_value=str(args.setup_motion or ""))
        motion_id = server.gui.add_text("motion_id", initial_value=str(args.setup_motion_id or ""))
        source_contact_layer = server.gui.add_text("source_contact_layer", initial_value=str(args.setup_source_contact_layer or ""))
        terrain_urdf = server.gui.add_text("terrain_urdf", initial_value=str(args.setup_terrain_urdf or ""))
        surface_catalog = server.gui.add_text("surface_catalog", initial_value=str(args.setup_surface_catalog or ""))

    with server.gui.add_folder("Session / Output"):
        session_name = server.gui.add_text("session_name", initial_value=str(args.setup_session_name or "contact_editor"))
        output_prefix = server.gui.add_text("output_prefix", initial_value=str(args.setup_output_prefix or ""))
        output_contact_layer = server.gui.add_text("output_contact_layer", initial_value=str(args.setup_output_contact_layer or ""))
        edit_plan = server.gui.add_text("edit_plan", initial_value=str(args.setup_edit_plan or ""))
        load_btn = server.gui.add_button("Open contact editor")

    with server.gui.add_folder("Viewer"):
        repo_root = server.gui.add_text("repo_root", initial_value=str(args.setup_repo_root or ""))
        with_terrain = server.gui.add_checkbox("show terrain", initial_value=bool(args.setup_with_terrain))
        default_mode = server.gui.add_dropdown("mode", options=("reject", "clamp"), initial_value=args.default_mode)
        show_only = server.gui.add_dropdown(
            "show_only",
            options=("all", "bound", "edited", "clamped", "suspicious", "failed", "unbound"),
            initial_value=args.show_only,
        )

    with server.gui.add_folder("Status"):
        status = server.gui.add_text("status", initial_value="Load a motion bundle, then open contact editor.", multiline=True)

    def _set_status(text: str) -> None:
        status.value = text
        print(f"[contact editor setup] {text}")

    def _load_config(config: ContactEditorConfig) -> None:
        _set_status("loading contact editor: preparing session and overlays...")
        next_state, prepared, terrain_urdf_for_viewer = _prepared_state_from_config(config)
        repo_path = Path(config.repo_root).expanduser() if config.repo_root else Path("/home/xiaz/holosoma_isaaclab3_newton")
        robot_urdf = repo_path / "OmniRetarget_Dataset/models/g1/g1_29dof_spherehand.urdf"
        object_urdf = config.terrain_urdf or terrain_urdf_for_viewer
        _set_status("loading contact editor: rendering motion and contact anchors...")
        motion_fps = _replace_motion_visuals(
            motion_path=config.motion,
            robot_urdf=robot_urdf if robot_urdf.exists() else None,
            object_urdf=object_urdf if config.with_terrain else None,
            fps_hint=int(args.fps or config.fps),
        )
        existing = controller_box.get("controller")
        if existing is not None:
            _remove_handles(existing.render_handles)
        controller = SurfaceEditorController.create(server, next_state)
        controller.edit_mode = str(args.edit_mode)
        controller.current_frame_getter = playback_slot.frame
        controller.timeline_port = int(args.timeline_port)
        controller.default_mode = str(default_mode.value)
        controller.show_only = str(show_only.value)
        controller.fps = motion_fps
        controller.robot_urdf = str(robot_urdf) if robot_urdf.exists() else None
        controller.terrain_urdf = str(object_urdf) if object_urdf and config.with_terrain else None
        if playback_slot.current is not None:
            playback_slot.current.frame_change_callback = controller.on_frame_changed

        def _reload_entry_in_process(entry: RecentMotionEntry) -> None:
            next_config = _contact_editor_config_from_recent_entry(entry)
            next_state_inner, prepared_inner, terrain_inner = _prepared_state_from_config(next_config)
            next_object_urdf = next_config.terrain_urdf or terrain_inner
            next_fps = _replace_motion_visuals(
                motion_path=next_config.motion,
                robot_urdf=controller.robot_urdf,
                object_urdf=next_object_urdf if next_config.with_terrain else None,
                fps_hint=int(args.fps or next_config.fps),
            )
            controller.state = next_state_inner
            controller.original_graph = copy.deepcopy(read_surface_editor_graph(next_state_inner.session))
            controller.undo_stack.clear()
            controller.redo_stack.clear()
            controller.terrain_urdf = str(next_object_urdf) if next_object_urdf and next_config.with_terrain else None
            controller.fps = next_fps
            if playback_slot.current is not None:
                playback_slot.current.frame_change_callback = controller.on_frame_changed
            controller.selected_anchor_id = controller.default_anchor_id()
            controller.state.selected_anchor_id = controller.selected_anchor_id
            controller.state.last_message = f"loaded motion: {Path(next_config.motion).name}"
            controller.state.last_error = None
            controller.reload_overlay()
            shell_controller.set_current(controller)
            upsert_recent_motion(entry)
            if callable(controller.on_change):
                controller.on_change()
            print(
                "[contact editor] reloaded motion in-place "
                f"{entry.label}: anchors={prepared_inner.ready_anchor_count} session={prepared_inner.session.session_dir}"
            )

        controller.reload_motion_callback = _reload_entry_in_process
        upsert_recent_motion(
            _recent_entry_from_session(
                next_state.session,
                label=Path(config.motion).stem,
                terrain_urdf=controller.terrain_urdf,
                metadata={"source": "contact_editor_setup"},
            )
        )
        controller.reload_overlay()
        _add_loaded_editor_sidebar(server, controller=controller, args=args, playback=playback_slot)
        controller_box["controller"] = controller
        shell_controller.set_current(controller)
        status.value = (
            f"Loaded {prepared.ready_anchor_count} anchors.\n"
            f"session={prepared.session.session_dir}\n"
            f"ready_layer={prepared.ready_layer}\n"
            f"editor=http://localhost:{shell_port}"
        )
        print(
            "[contact editor] loaded in-process "
            f"motion={config.motion} anchors={prepared.ready_anchor_count} "
            f"user_url=http://localhost:{shell_port}"
        )

    def _start_loaded_editor() -> None:
        _set_status("loading contact editor: validating inputs...")
        if not str(motion.value).strip():
            raise ValueError("motion_npz is required")
        if not str(motion_id.value).strip():
            raise ValueError("motion_id is required")
        if not str(source_contact_layer.value).strip():
            raise ValueError("source_contact_layer is required")
        _load_config(
            ContactEditorConfig(
                motion=str(motion.value).strip(),
                motion_id=str(motion_id.value).strip(),
                source_contact_layer=str(source_contact_layer.value).strip(),
                session_name=str(session_name.value).strip() or "contact_editor",
                surface_catalog=str(surface_catalog.value).strip() or None,
                terrain_urdf=str(terrain_urdf.value).strip() or None,
                output_prefix=str(output_prefix.value).strip() or None,
                edit_plan=str(edit_plan.value).strip() or None,
                output_contact_layer=str(output_contact_layer.value).strip() or None,
                repo_root=str(repo_root.value).strip() or None,
                with_terrain=bool(with_terrain.value),
                bind_mode=str(default_mode.value),
                fps=int(args.fps),
            )
        )

    def _apply_selected_load_file(selected_type: str, selected_path: Path) -> None:
        selected = str(selected_path)
        if selected_type == "Motion":
            record = read_motion_asset(selected_path.stem, selected_path)
            motion.value = record.motion_path
            motion_id.value = record.motion_id or record.motion_asset_id
            if record.terrain_urdf:
                terrain_urdf.value = record.terrain_urdf
                with_terrain.value = True
            if record.surface_catalog_path:
                surface_catalog.value = record.surface_catalog_path
            derived = record.derived or {}
            if derived.get("bound_contact_layer") or derived.get("contact_layer"):
                source_contact_layer.value = derived.get("bound_contact_layer") or derived.get("contact_layer")
            if derived.get("edit_plan_path"):
                edit_plan.value = derived.get("edit_plan_path")
            if derived.get("output_contact_layer"):
                output_contact_layer.value = derived.get("output_contact_layer")
            if not str(session_name.value).strip() or str(session_name.value) == "contact_editor":
                session_name.value = f"{record.motion_asset_id}_contact_editor"
            if not str(output_prefix.value).strip():
                output_prefix.value = f"contact/{record.motion_asset_id}_contact_editor"
            _set_status(f"loaded motion: {record.motion_asset_id}")
            _start_loaded_editor()
        elif selected_type == "Motion NPZ":
            motion.value = selected
            if not str(motion_id.value).strip():
                motion_id.value = selected_path.stem
            if not str(session_name.value).strip() or str(session_name.value) == "contact_editor":
                session_name.value = f"{selected_path.stem}_contact_editor"
            _set_status(f"selected motion: {selected}")
        elif selected_type == "Contact Layer":
            source_contact_layer.value = _layer_name_from_path(selected_path)
            _set_status(f"selected contact layer: {source_contact_layer.value}")
        elif selected_type == "Terrain URDF":
            terrain_urdf.value = selected
            with_terrain.value = True
            _set_status(f"selected terrain URDF: {selected}")
        elif selected_type == "Surface Catalog":
            surface_catalog.value = selected
            _set_status(f"selected surface catalog: {selected}")
        else:
            raise ValueError(f"unknown load type: {selected_type}")

    @browse_btn.on_click
    def _(_) -> None:
        try:
            selected_type = str(load_type.value)
            selected = _filtered_open_file_dialog(
                title=f"Load {selected_type}",
                load_type=selected_type,
            )
            if not selected:
                _set_status(f"no {selected_type} selected")
                return
            _set_status(f"loading {selected_type}: {selected}")
            _apply_selected_load_file(selected_type, Path(selected))
        except Exception as exc:
            print(f"[contact editor setup] browse failed: {exc}", file=sys.stderr)
            _set_status(f"browse failed: {exc}")

    @save_as_btn.on_click
    def _(_) -> None:
        try:
            selected_type = str(save_type.value)
            config = _setup_save_dialog_config(selected_type)
            selected = _save_file_dialog(
                title=config["title"],
                defaultextension=config["defaultextension"],
                filetypes=config["filetypes"],
                initialdir=config["initialdir"],
            )
            if not selected:
                return
            if selected_type == "Output Contact Layer":
                output_contact_layer.value = _layer_name_from_path(selected)
                _set_status(f"output contact layer: {output_contact_layer.value}")
            elif selected_type == "Edit Plan":
                edit_plan.value = selected
                _set_status(f"edit plan: {selected}")
            else:
                raise ValueError(f"unknown save type: {selected_type}")
        except Exception as exc:
            _set_status(f"save picker failed: {exc}")

    @load_btn.on_click
    def _(_) -> None:
        try:
            _start_loaded_editor()
        except Exception as exc:
            print(f"[contact editor setup] Load failed: {exc}", file=sys.stderr)
            _set_status(f"Load failed: {exc}")

    shell_controller.load_recent_callback = lambda entry: _load_config(_contact_editor_config_from_recent_entry(entry))

    print(f"[contact editor setup] Open Contact Editor: http://localhost:{shell_port}")
    print("Fill setup fields in the Viser UI and click Load contact editor.")
    if str(args.setup_motion or "").strip():
        try:
            _start_loaded_editor()
        except Exception as exc:
            print(f"[contact editor setup] auto-load failed: {exc}", file=sys.stderr)
            _set_status(f"auto-load failed: {exc}")
    while True:
        time.sleep(0.2)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Viser surface binding overlay player.")
    parser.add_argument("--setup-mode", action="store_true")
    parser.add_argument("--setup-motion", default="")
    parser.add_argument("--setup-motion-id", default="")
    parser.add_argument("--setup-source-contact-layer", default="")
    parser.add_argument("--setup-terrain-urdf", default="")
    parser.add_argument("--setup-surface-catalog", default="")
    parser.add_argument("--setup-session-name", default="")
    parser.add_argument("--setup-output-prefix", default="")
    parser.add_argument("--setup-output-contact-layer", default="")
    parser.add_argument("--setup-edit-plan", default="")
    parser.add_argument("--setup-repo-root", default="")
    parser.add_argument("--setup-with-terrain", action="store_true")
    parser.add_argument("--qpos-npz", default=None)
    parser.add_argument("--surface-binding-overlay", default=None)
    parser.add_argument("--surface-editor-session", default=None)
    parser.add_argument("--surface-editor-requests", default=None)
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
