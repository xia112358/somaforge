from __future__ import annotations

import copy
import socket
import threading
import webbrowser
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from somaforge_core.robot_assets import canonical_g1_urdf_path, somaforge_root

from motion_edit.contact import read_contact_surfaces
from motion_edit.contact.plans import read_contact_edit_plan, validate_contact_edit_plan, write_contact_edit_plan
from motion_edit.paths import LAYERS_ROOT, WORKBENCH_ROOT
from motion_edit.storage import list_motion_assets, read_motion_asset
from motion_edit.workbench.contact_editor_setup import ContactEditorConfig, prepare_contact_editor_session
from motion_edit.workbench.surface_editor_session import (
    SurfaceEditorSession,
    move_surface_editor_anchor,
    read_pending_surface_edits,
    read_surface_editor_graph,
    save_surface_editor_session,
    write_pending_surface_edits,
    write_surface_editor_graph,
)

from .motion_data import load_contact_force_payload, load_motion_sequence

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = PACKAGE_ROOT / "motion_edit" / "web_dist"


class LoadRequest(BaseModel):
    motion_asset_id: str


class MoveRequest(BaseModel):
    anchor_id: str
    requested_world_position: list[float] | None = None
    tangent_delta: list[float] | None = None
    target_uv: list[float] | None = None
    mode: str = "reject"


class SettingsRequest(BaseModel):
    edit_plan_path: str | None = None
    output_contact_layer: str | None = None


@dataclass
class EditorState:
    session: SurfaceEditorSession | None = None
    motion_asset_id: str | None = None
    undo_stack: list[tuple[Any, list[Any]]] = field(default_factory=list)
    redo_stack: list[tuple[Any, list[Any]]] = field(default_factory=list)
    initial_snapshot: tuple[Any, list[Any]] | None = None

    def snapshot(self) -> tuple[Any, list[Any]]:
        if self.session is None:
            raise ValueError("no motion is loaded")
        return copy.deepcopy(read_surface_editor_graph(self.session)), copy.deepcopy(read_pending_surface_edits(self.session))

    def restore(self, snapshot: tuple[Any, list[Any]]) -> None:
        if self.session is None:
            raise ValueError("no motion is loaded")
        graph, edits = snapshot
        write_surface_editor_graph(self.session, graph)
        write_pending_surface_edits(self.session, edits)


def _repo_url(path: str | Path) -> str:
    resolved = Path(path).expanduser().resolve()
    root = somaforge_root().resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"asset is outside the Somaforge repository: {resolved}") from exc
    return "/repo/" + relative.as_posix()


def _asset_config(asset_id: str) -> ContactEditorConfig:
    record = read_motion_asset(asset_id)
    source_contact_layer = record.source_contact_layer
    if not source_contact_layer:
        raise ValueError(f"{asset_id} has no contact layer")
    return ContactEditorConfig(
        motion=record.contact_force_npz or record.motion_path,
        motion_id=record.motion_id or record.motion_asset_id,
        source_contact_layer=source_contact_layer,
        session_name=f"{record.motion_asset_id}_web_contact_editor",
        surface_catalog=record.surface_catalog_path,
        terrain_urdf=record.terrain_urdf,
        terrain_mesh=record.terrain_mesh,
        output_prefix=f"contact/{record.motion_asset_id}_web_contact_editor",
        edit_plan=record.edit_plan_path or str(WORKBENCH_ROOT / "plans" / f"{record.motion_asset_id}.contact_edit_plan.json"),
        output_contact_layer=record.output_contact_layer or f"contact/{record.motion_asset_id}_edited",
        with_terrain=bool(record.terrain_urdf or record.terrain_mesh or record.surface_catalog_path),
        fps=int(record.fps or 50),
    )


def _session_payload(state: EditorState) -> dict[str, Any]:
    if state.session is None or state.motion_asset_id is None:
        raise ValueError("no motion is loaded")
    record = read_motion_asset(state.motion_asset_id)
    session = state.session
    graph = read_surface_editor_graph(session)
    surfaces = read_contact_surfaces(session.surface_catalog) if session.surface_catalog else []
    qpos, fps, joint_names = load_motion_sequence(session.motion_path)
    force = load_contact_force_payload(record.contact_force_npz or record.motion_path, frame_count=qpos.shape[0])
    return {
        "motion_asset_id": state.motion_asset_id,
        "motion_id": session.motion_id,
        "fps": fps,
        "qpos": qpos.tolist(),
        "joint_names": list(joint_names),
        "robot_urdf_url": _repo_url(canonical_g1_urdf_path()),
        "terrain_obj_url": _repo_url(record.terrain_mesh) if record.terrain_mesh else None,
        "graph": graph.to_dict(),
        "surfaces": [surface.to_dict() for surface in surfaces],
        "contact_force": force,
        "pending_edit_count": len(read_pending_surface_edits(session)),
        "can_undo": bool(state.undo_stack),
        "can_redo": bool(state.redo_stack),
        "settings": {
            "edit_plan_path": session.edit_plan_path,
            "output_contact_layer": session.output_contact_layer,
            "source_contact_layer": session.contact_layer,
        },
        "plan": _plan_payload(session.edit_plan_path),
    }


def _plan_payload(path: str | None) -> dict[str, Any] | None:
    if not path or not Path(path).expanduser().exists():
        return None
    plan = read_contact_edit_plan(path)
    return {"path": str(Path(path).expanduser()), "status": plan.status, "edit_count": len(plan.edits)}


def _save_session(state: EditorState, *, validate: bool = False) -> dict[str, Any]:
    if state.session is None:
        raise ValueError("no motion is loaded")
    plan_path = Path(state.session.edit_plan_path).expanduser() if state.session.edit_plan_path else None
    output = save_surface_editor_session(state.session, layers_root=LAYERS_ROOT)
    warnings: list[str] = []
    if validate:
        if plan_path is None or not plan_path.exists():
            raise ValueError("no ContactEditPlan was written; edit at least one anchor before validation")
        plan = read_contact_edit_plan(plan_path)
        if not plan.edits:
            raise ValueError("ContactEditPlan has no edits; edit at least one anchor before validation")
        warnings = validate_contact_edit_plan(plan)
        write_contact_edit_plan(plan_path, replace(plan, status="validated"))
    return {
        "output_contact_layer": str(output) if output else None,
        "pending_edit_count": len(read_pending_surface_edits(state.session)),
        "plan": _plan_payload(state.session.edit_plan_path),
        "warnings": warnings,
    }


def create_app(*, initial_motion_asset_id: str | None = None) -> FastAPI:
    app = FastAPI(title="Motion Edit Contact Editor")
    state = EditorState()
    app.mount("/repo", StaticFiles(directory=str(somaforge_root())), name="repo")

    @app.get("/api/assets")
    def assets() -> dict:
        return {
            "assets": [
                {
                    "motion_asset_id": item.motion_asset_id,
                    "motion_id": item.motion_id or item.motion_asset_id,
                    "source": item.source,
                    "has_force": bool(item.contact_force_npz),
                    "has_terrain": bool(item.terrain_mesh or item.terrain_urdf or item.surface_catalog_path),
                }
                for item in list_motion_assets()
            ]
        }

    @app.post("/api/session/load")
    def load(request: LoadRequest) -> dict:
        try:
            prepared = prepare_contact_editor_session(
                _asset_config(request.motion_asset_id), layers_root=LAYERS_ROOT, workbench_root=WORKBENCH_ROOT
            )
            state.session = prepared.session
            state.motion_asset_id = request.motion_asset_id
            state.undo_stack.clear()
            state.redo_stack.clear()
            state.initial_snapshot = state.snapshot()
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/session")
    def session() -> dict:
        try:
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/session/move")
    def move(request: MoveRequest) -> dict:
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            before = state.snapshot()
            requested = request.requested_world_position
            tangent = request.tangent_delta
            if request.target_uv is not None:
                graph = read_surface_editor_graph(state.session)
                anchor = next((item for item in graph.anchors if item.anchor_id == request.anchor_id), None)
                if anchor is None or not anchor.surface_coordinates:
                    raise ValueError(f"{request.anchor_id} has no surface coordinates")
                tangent = [
                    float(request.target_uv[0]) - float(anchor.surface_coordinates["u"]),
                    float(request.target_uv[1]) - float(anchor.surface_coordinates["v"]),
                ]
                requested = None
            if requested is None and tangent is None:
                raise ValueError("move requires requested_world_position, tangent_delta, or target_uv")
            move_surface_editor_anchor(
                state.session,
                anchor_id=request.anchor_id,
                requested_world_position=requested,
                tangent_delta=tangent,
                mode=request.mode,
            )
            state.undo_stack.append(before)
            state.redo_stack.clear()
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/undo")
    def undo() -> dict:
        if state.session is None or not state.undo_stack:
            raise HTTPException(status_code=409, detail="nothing to undo")
        state.redo_stack.append(state.snapshot())
        state.restore(state.undo_stack.pop())
        return _session_payload(state)

    @app.post("/api/session/redo")
    def redo() -> dict:
        if state.session is None or not state.redo_stack:
            raise HTTPException(status_code=409, detail="nothing to redo")
        state.undo_stack.append(state.snapshot())
        state.restore(state.redo_stack.pop())
        return _session_payload(state)

    @app.post("/api/session/save")
    def save() -> dict:
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            return _save_session(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/validate")
    def validate() -> dict:
        try:
            return _save_session(state, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/restore-anchor")
    def restore_anchor(request: MoveRequest) -> dict:
        if state.session is None or state.initial_snapshot is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            original_graph, _ = state.initial_snapshot
            original = next((item for item in original_graph.anchors if item.anchor_id == request.anchor_id), None)
            if original is None or original.world_position is None:
                raise ValueError(f"initial anchor not found: {request.anchor_id}")
            before = state.snapshot()
            move_surface_editor_anchor(
                state.session,
                anchor_id=request.anchor_id,
                requested_world_position=original.world_position,
                mode=request.mode,
            )
            state.undo_stack.append(before)
            state.redo_stack.clear()
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/reset")
    def reset() -> dict:
        if state.session is None or state.initial_snapshot is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        state.restore(copy.deepcopy(state.initial_snapshot))
        state.undo_stack.clear()
        state.redo_stack.clear()
        return _session_payload(state)

    @app.post("/api/session/discard")
    def discard() -> dict:
        return reset()

    @app.post("/api/session/reload")
    def reload() -> dict:
        if state.motion_asset_id is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            prepared = prepare_contact_editor_session(
                _asset_config(state.motion_asset_id), layers_root=LAYERS_ROOT, workbench_root=WORKBENCH_ROOT
            )
            state.session = prepared.session
            state.undo_stack.clear()
            state.redo_stack.clear()
            state.initial_snapshot = state.snapshot()
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/session/settings")
    def settings(request: SettingsRequest) -> dict:
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        state.session = replace(
            state.session,
            edit_plan_path=request.edit_plan_path or state.session.edit_plan_path,
            output_contact_layer=request.output_contact_layer or state.session.output_contact_layer,
        )
        return _session_payload(state)

    @app.get("/")
    def index() -> FileResponse:
        target = WEB_DIST / "index.html"
        if not target.exists():
            raise HTTPException(status_code=503, detail="web frontend is not built; run npm run build in packages/motion_edit/web")
        return FileResponse(target)

    if WEB_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="web-assets")

    if initial_motion_asset_id:
        @app.on_event("startup")
        def load_initial() -> None:
            prepared = prepare_contact_editor_session(
                _asset_config(initial_motion_asset_id), layers_root=LAYERS_ROOT, workbench_root=WORKBENCH_ROOT
            )
            state.session = prepared.session
            state.motion_asset_id = initial_motion_asset_id
            state.initial_snapshot = state.snapshot()
    return app


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", int(port))) != 0


def run_contact_editor(*, motion_asset_id: str | None, host: str = "127.0.0.1", port: int = 8094, open_browser: bool = True) -> None:
    import uvicorn

    if not _port_available(port):
        raise RuntimeError(f"contact editor port {port} is already in use")
    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Motion Edit Contact Editor: {url}")
    uvicorn.run(create_app(initial_motion_asset_id=motion_asset_id), host=host, port=port, log_level="info")
