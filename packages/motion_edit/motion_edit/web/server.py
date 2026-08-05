from __future__ import annotations

import copy
import socket
import threading
import time
import webbrowser
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from somaforge_core.robot_assets import canonical_g1_urdf_path, somaforge_root

from motion_edit.contact import read_contact_surfaces
from motion_edit.contact.plans import read_contact_edit_plan, validate_contact_edit_plan, write_contact_edit_plan
from motion_edit.generation.contact_aware import ContactAwareGenerationResult, apply_contact_aware_edit_plan_to_motion
from motion_edit.paths import LAYERS_ROOT, WORKBENCH_ROOT
from motion_edit.storage import (
    MotionVersionRecord,
    list_motion_assets,
    list_motion_versions,
    read_motion_asset,
    read_motion_version,
    write_motion_version,
)
from motion_edit.workbench.contact_editor_setup import ContactEditorConfig, prepare_contact_editor_session
from motion_edit.workbench.edit_handles import (
    build_contact_episode_handles,
    contact_episode_handle_payloads as _edit_handle_payloads,
)
from motion_edit.workbench.recent import (
    RecentMotionEntry,
    clear_recent_motions,
    read_recent_motions,
    upsert_recent_motion,
)
from motion_edit.workbench.surface_editor_session import (
    SurfaceEditorSession,
    move_surface_editor_anchor,
    move_surface_editor_handle,
    prepare_playback_surface_editor_session,
    read_pending_surface_edits,
    read_surface_editor_graph,
    restore_surface_editor_handle,
    save_surface_editor_session,
    write_pending_surface_edits,
    write_surface_editor_graph,
)

from .motion_data import load_contact_force_payload, load_motion_sequence

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = PACKAGE_ROOT / "motion_edit" / "web_dist"
EDITOR_CONTACT_MAX_GAP_FRAMES = 10
EDITOR_CONTACT_MIN_DURATION_FRAMES = 20


def _editor_contact_handles(anchors: Any) -> list[Any]:
    return build_contact_episode_handles(
        anchors,
        max_gap_frames=EDITOR_CONTACT_MAX_GAP_FRAMES,
        min_duration_frames=EDITOR_CONTACT_MIN_DURATION_FRAMES,
    )


class LoadRequest(BaseModel):
    motion_id: str


class MoveRequest(BaseModel):
    anchor_id: str
    requested_world_position: list[float] | None = None
    tangent_delta: list[float] | None = None
    target_uv: list[float] | None = None
    mode: str = "reject"


class HandleMoveRequest(BaseModel):
    handle_id: str
    requested_world_position: list[float] | None = None
    tangent_delta: list[float] | None = None
    target_uv: list[float] | None = None
    mode: str = "reject"


class SettingsRequest(BaseModel):
    edit_plan_path: str | None = None
    output_contact_layer: str | None = None
    output_motion_path: str | None = None
    output_segment_layer: str | None = None
    output_motion_id: str | None = None
    register_motion: bool | None = None
    overwrite: bool | None = None


class GenerateRequest(BaseModel):
    output_motion_path: str | None = None
    output_segment_layer: str | None = None
    output_motion_id: str | None = None
    register_motion: bool | None = None
    overwrite: bool | None = None


@dataclass
class GenerationJob:
    status: str = "idle"
    stage: str | None = None
    output_motion_path: str | None = None
    output_motion_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stage": self.stage,
            "output_motion_path": self.output_motion_path,
            "output_motion_id": self.output_motion_id,
            "warnings": list(self.warnings),
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class EditorState:
    session: SurfaceEditorSession | None = None
    motion_id: str | None = None
    motion_provenance: str = "source"
    # Compatibility lineage used by generation and context resolution only.
    motion_asset_id: str | None = None
    motion_version_id: str | None = None
    read_only: bool = False
    fps: float = 50.0
    undo_stack: list[tuple[Any, list[Any]]] = field(default_factory=list)
    redo_stack: list[tuple[Any, list[Any]]] = field(default_factory=list)
    initial_snapshot: tuple[Any, list[Any]] | None = None
    output_motion_path: str | None = None
    output_segment_layer: str | None = None
    output_motion_id: str | None = None
    register_motion: bool = True
    overwrite: bool = False
    generation: GenerationJob = field(default_factory=GenerationJob)
    generation_lock: threading.Lock = field(default_factory=threading.Lock)
    generation_worker: threading.Thread | None = None

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

    def generation_payload(self) -> dict[str, Any]:
        with self.generation_lock:
            worker = self.generation_worker
            if (
                self.generation.status == "running"
                and worker is not None
                and worker.ident is not None
                and not worker.is_alive()
            ):
                self.generation.status = "failed"
                self.generation.stage = "failed"
                self.generation.error = "generation worker exited before reporting a result"
                self.generation.finished_at = time.time()
            return self.generation.to_dict()


def _require_generation_idle(state: EditorState) -> None:
    if state.generation_payload()["status"] == "running":
        raise HTTPException(status_code=409, detail="the ContactEditPlan is locked while generation is running")


def _require_editable(state: EditorState) -> None:
    if state.read_only:
        raise HTTPException(
            status_code=409,
            detail="motion is loaded in playback-only mode because it has no contact layer",
        )


def _repo_url(path: str | Path) -> str:
    root = somaforge_root().resolve()
    candidate = Path(path).expanduser()
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"asset is outside the Somaforge repository: {resolved}") from exc
    return "/repo/" + relative.as_posix()


def _repo_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = somaforge_root() / candidate
    return str(candidate.resolve())


@dataclass(frozen=True)
class EditorMotion:
    motion_id: str
    motion_asset_id: str
    motion_version_id: str | None
    motion_path: str
    provenance: str


def _motion_provenance(version: MotionVersionRecord | None) -> str:
    if version is None:
        return "source"
    return str(version.metadata.get("provenance") or version.kind)


def _resolve_motion(motion_id: str) -> EditorMotion:
    try:
        version = read_motion_version(motion_id)
    except FileNotFoundError:
        asset = read_motion_asset(motion_id)
        return EditorMotion(
            motion_id=asset.motion_asset_id,
            motion_asset_id=asset.motion_asset_id,
            motion_version_id=None,
            motion_path=asset.motion_path,
            provenance="source",
        )
    if not version.motion_asset_id:
        raise ValueError(f"{motion_id} has no Motion context binding")
    asset = read_motion_asset(version.motion_asset_id)
    return EditorMotion(
        motion_id=version.motion_version_id,
        motion_asset_id=asset.motion_asset_id,
        motion_version_id=version.motion_version_id,
        motion_path=version.motion_path,
        provenance=_motion_provenance(version),
    )


def _list_editor_motions() -> list[EditorMotion]:
    motions = {
        asset.motion_asset_id: EditorMotion(
            motion_id=asset.motion_asset_id,
            motion_asset_id=asset.motion_asset_id,
            motion_version_id=None,
            motion_path=asset.motion_path,
            provenance="source",
        )
        for asset in list_motion_assets()
    }
    for version in list_motion_versions():
        if not version.motion_asset_id:
            continue
        try:
            motion = _resolve_motion(version.motion_version_id)
        except (FileNotFoundError, ValueError):
            continue
        if motion.motion_id in motions:
            raise ValueError(f"duplicate unified Motion ID: {motion.motion_id}")
        motions[motion.motion_id] = motion
    return [motions[key] for key in sorted(motions)]


def _motion_config(motion_id: str) -> ContactEditorConfig:
    motion = _resolve_motion(motion_id)
    record = read_motion_asset(motion.motion_asset_id)
    version = (
        read_motion_version(motion.motion_version_id)
        if motion.motion_version_id
        else None
    )
    source_contact_layer = version.contact_layer if version is not None else record.source_contact_layer
    if not source_contact_layer:
        raise ValueError(f"{motion.motion_id} has no contact layer")
    identity = motion.motion_id
    return ContactEditorConfig(
        motion=_repo_path(motion.motion_path) or motion.motion_path,
        motion_id=record.motion_id or record.motion_asset_id,
        source_contact_layer=source_contact_layer,
        session_name=f"{identity}_web_contact_editor",
        surface_catalog=_repo_path(record.surface_catalog_path),
        terrain_urdf=_repo_path(record.terrain_urdf),
        terrain_mesh=_repo_path(record.terrain_mesh),
        output_prefix=f"contact/{identity}_web_contact_editor",
        edit_plan=(
            str(WORKBENCH_ROOT / "plans" / f"{identity}.contact_edit_plan.json")
            if version is not None
            else (record.edit_plan_path or str(WORKBENCH_ROOT / "plans" / f"{identity}.contact_edit_plan.json"))
        ),
        output_contact_layer=(f"contact/{identity}_edited" if version is not None else (record.output_contact_layer or f"contact/{identity}_edited")),
        with_terrain=bool(record.terrain_urdf or record.terrain_mesh or record.surface_catalog_path),
        fps=int(record.fps or 50),
        prebound_contact_layer=version is not None or bool(record.bound_contact_layer),
        contact_force_motion=_repo_path(
            version.motion_path if version is not None else record.contact_force_npz
        ),
    )


def _reset_generation_settings(state: EditorState, motion_id: str) -> None:
    motion = _resolve_motion(motion_id)
    record = read_motion_asset(motion.motion_asset_id)
    stem = f"{motion.motion_id}_edited"
    output_motion_path = _default_output_motion_path(motion.motion_id)
    state.output_motion_path = str(output_motion_path)
    state.output_segment_layer = (
        f"candidates/{stem}"
        if motion.motion_version_id
        else (record.output_segment_layer or f"candidates/{stem}")
    )
    state.output_motion_id = stem
    state.register_motion = True
    state.overwrite = output_motion_path.exists()
    state.fps = float(record.fps or 50.0)
    with state.generation_lock:
        state.generation = GenerationJob()
        state.generation_worker = None


def _apply_generation_settings(state: EditorState, request: SettingsRequest | GenerateRequest) -> None:
    if request.output_motion_path is not None:
        state.output_motion_path = request.output_motion_path.strip()
    if request.output_segment_layer is not None:
        state.output_segment_layer = request.output_segment_layer.strip()
    if request.output_motion_id is not None:
        state.output_motion_id = request.output_motion_id.strip()
    if request.register_motion is not None:
        state.register_motion = request.register_motion
    if request.overwrite is not None:
        state.overwrite = request.overwrite
    if state.motion_id and state.output_motion_path:
        output_path = Path(state.output_motion_path).expanduser()
        default_path = _default_output_motion_path(state.motion_id)
        if output_path == default_path and default_path.exists():
            state.overwrite = True


def _default_output_motion_path(motion_id: str) -> Path:
    stem = f"{motion_id}_edited"
    return PACKAGE_ROOT / "data" / "motions" / "generated" / f"{stem}.policy_ref_v1.npz"


def _recent_entry(motion_id: str) -> RecentMotionEntry:
    motion = _resolve_motion(motion_id)
    asset = read_motion_asset(motion.motion_asset_id)
    version = (
        read_motion_version(motion.motion_version_id)
        if motion.motion_version_id
        else None
    )
    return RecentMotionEntry(
        label=motion.motion_id,
        motion_path=_repo_path(motion.motion_path) or motion.motion_path,
        motion_id=asset.motion_id or asset.motion_asset_id,
        motion_ref_id=motion.motion_id,
        motion_asset_id=asset.motion_asset_id,
        motion_version_id=motion.motion_version_id,
        terrain_urdf=asset.terrain_urdf,
        contact_layer=version.contact_layer if version is not None else asset.source_contact_layer,
        surface_catalog=_repo_path(asset.surface_catalog_path),
        edit_plan_path=(
            str(WORKBENCH_ROOT / "plans" / f"{motion.motion_id}.contact_edit_plan.json")
            if motion.motion_version_id
            else asset.edit_plan_path
        ),
        output_contact_layer=(
            f"contact/{motion.motion_id}_edited"
            if motion.motion_version_id
            else asset.output_contact_layer
        ),
        output_segment_layer=(
            f"candidates/{motion.motion_id}_edited"
            if motion.motion_version_id
            else asset.output_segment_layer
        ),
        metadata={"provenance": motion.provenance},
    )


def _recent_payload(state: EditorState) -> dict[str, Any]:
    active_motion_id = state.motion_id
    items = []
    for entry in read_recent_motions():
        motion_id = entry.motion_ref_id
        if not motion_id:
            continue
        items.append(
            {
                "label": entry.label,
                "motion_id": motion_id,
                "provenance": entry.metadata.get("provenance", "source"),
                "active": motion_id == active_motion_id,
                "last_opened_at": entry.last_opened_at,
            }
        )
    return {"items": items, "active_motion_id": active_motion_id}


def _open_motion(state: EditorState, motion_id: str) -> dict[str, Any]:
    motion = _resolve_motion(motion_id)
    record = read_motion_asset(motion.motion_asset_id)
    version = read_motion_version(motion.motion_version_id) if motion.motion_version_id else None
    source_contact_layer = version.contact_layer if version is not None else record.source_contact_layer
    if source_contact_layer:
        prepared = prepare_contact_editor_session(
            _motion_config(motion.motion_id),
            layers_root=LAYERS_ROOT,
            workbench_root=WORKBENCH_ROOT,
        )
        state.session = prepared.session
        state.read_only = False
    else:
        state.session = prepare_playback_surface_editor_session(
            motion_path=_repo_path(motion.motion_path) or motion.motion_path,
            motion_id=record.motion_id or record.motion_asset_id,
            surface_catalog=_repo_path(record.surface_catalog_path),
            session_name=f"{motion.motion_id}_web_playback",
            workbench_root=WORKBENCH_ROOT,
        )
        state.read_only = True
    state.motion_id = motion.motion_id
    state.motion_provenance = motion.provenance
    state.motion_asset_id = motion.motion_asset_id
    state.motion_version_id = motion.motion_version_id
    state.undo_stack.clear()
    state.redo_stack.clear()
    state.initial_snapshot = state.snapshot()
    _reset_generation_settings(state, motion.motion_id)
    upsert_recent_motion(_recent_entry(motion.motion_id))
    return _session_payload(state)


def _session_payload(state: EditorState) -> dict[str, Any]:
    if state.session is None or state.motion_id is None or state.motion_asset_id is None:
        raise ValueError("no motion is loaded")
    record = read_motion_asset(state.motion_asset_id)
    session = state.session
    graph = read_surface_editor_graph(session)
    handles = _editor_contact_handles(graph.anchors)
    initial_handles = (
        _editor_contact_handles(state.initial_snapshot[0].anchors)
        if state.initial_snapshot is not None
        else handles
    )
    surfaces = read_contact_surfaces(session.surface_catalog) if session.surface_catalog else []
    qpos, fps, joint_names = load_motion_sequence(session.motion_path)
    state.fps = float(fps)
    force = load_contact_force_payload(session.contact_force_path or session.motion_path, frame_count=qpos.shape[0])
    return {
        "motion_id": state.motion_id,
        "read_only": state.read_only,
        "capabilities": {
            "playback": True,
            "edit_contacts": not state.read_only,
            "generate": not state.read_only,
        },
        "provenance": state.motion_provenance,
        "source_motion_id": session.motion_id,
        "fps": fps,
        "qpos": qpos.tolist(),
        "joint_names": list(joint_names),
        "robot_urdf_url": _repo_url(canonical_g1_urdf_path()),
        "terrain_obj_url": _repo_url(record.terrain_mesh) if record.terrain_mesh else None,
        "graph": graph.to_dict(),
        "edit_handles": _edit_handle_payloads(handles, initial_handles),
        "surfaces": [surface.to_dict() for surface in surfaces],
        "contact_force": force,
        "pending_edit_count": _edit_operation_count(read_pending_surface_edits(session)),
        "can_undo": bool(state.undo_stack),
        "can_redo": bool(state.redo_stack),
        "settings": {
            "edit_plan_path": session.edit_plan_path,
            "output_contact_layer": session.output_contact_layer,
            "source_contact_layer": session.contact_layer,
            "output_motion_path": state.output_motion_path,
            "output_segment_layer": state.output_segment_layer,
            "output_motion_id": state.output_motion_id,
            "register_motion": state.register_motion,
            "overwrite": state.overwrite,
        },
        "plan": _plan_payload(session.edit_plan_path),
        "generation": state.generation_payload(),
    }


def _plan_payload(path: str | None) -> dict[str, Any] | None:
    if not path or not Path(path).expanduser().exists():
        return None
    plan = read_contact_edit_plan(path)
    return {
        "path": str(Path(path).expanduser()),
        "status": plan.status,
        "edit_count": _edit_operation_count(plan.edits),
        "surface_transform_count": len(plan.surface_transforms),
        "pose_edit_count": len(plan.pose_edits),
        "contact_episode_count": int(plan.metadata.get("contact_episode_count", 0)),
        "anchor_constraint_count": int(plan.metadata.get("anchor_constraint_count", 0)),
    }


def _edit_operation_count(edits: list[Any]) -> int:
    operations: set[str] = set()
    for index, edit in enumerate(edits):
        metadata = edit.metadata if hasattr(edit, "metadata") else edit.get("metadata", {})
        anchor_id = edit.anchor_id if hasattr(edit, "anchor_id") else edit.get("anchor_id")
        operations.add(str(metadata.get("editor_handle_id") or anchor_id or index))
    return len(operations)


def _save_session(state: EditorState, *, validate: bool = False) -> dict[str, Any]:
    if state.session is None:
        raise ValueError("no motion is loaded")
    plan_path = Path(state.session.edit_plan_path).expanduser() if state.session.edit_plan_path else None
    previous_plan = read_contact_edit_plan(plan_path) if plan_path is not None and plan_path.exists() else None
    output = save_surface_editor_session(state.session, layers_root=LAYERS_ROOT)
    warnings: list[str] = []
    if plan_path is not None and plan_path.exists():
        plan = read_contact_edit_plan(plan_path)
        status = "draft"
        if previous_plan is not None and previous_plan.edits == plan.edits:
            same_outputs = (
                previous_plan.output_motion_path == state.output_motion_path
                and previous_plan.output_contact_layer == state.session.output_contact_layer
                and previous_plan.output_segment_layer == state.output_segment_layer
            )
            if previous_plan.status == "generated" and same_outputs:
                status = "generated"
            elif previous_plan.status in {"validated", "locked", "generated"}:
                status = "validated"
        write_contact_edit_plan(
            plan_path,
            replace(
                plan,
                status=status,
                output_motion_path=state.output_motion_path,
                output_contact_layer=state.session.output_contact_layer,
                output_segment_layer=state.output_segment_layer,
            ),
        )
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
        "pending_edit_count": _edit_operation_count(read_pending_surface_edits(state.session)),
        "plan": _plan_payload(state.session.edit_plan_path),
        "warnings": warnings,
    }


def _run_generation(
    state: EditorState,
    generation_fn: Callable[..., ContactAwareGenerationResult],
    *,
    plan_path: Path,
    source_contact_layer: str,
    output_contact_layer: str,
    output_motion_path: str,
    output_segment_layer: str | None,
    output_motion_id: str | None,
    register_motion: bool,
    overwrite: bool,
    fps: float,
    motion_asset_id: str | None = None,
    parent_motion_version_id: str | None = None,
    force_source_motion_path: str | None = None,
) -> None:
    def update_stage(stage: str) -> None:
        with state.generation_lock:
            state.generation.stage = stage

    try:
        update_stage("reading_plan")
        plan = read_contact_edit_plan(plan_path)
        result = generation_fn(
            plan,
            output_motion_path=output_motion_path,
            bake_force=False,
            overwrite=overwrite,
            source_plan_path=plan_path,
            source_contact_layer=source_contact_layer,
            force_source_motion_path=force_source_motion_path,
            output_contact_layer=output_contact_layer,
            output_segment_layer=output_segment_layer,
            output_motion_version_id=output_motion_id,
            fps=fps,
            register_motion_version=register_motion,
            fullbody_solver="batch_contact_laplacian",
            contact_laplacian_iters=8,
            contact_laplacian_damping=1.0e-4,
            contact_laplacian_trust=0.05,
            edit_contact_weight=1000.0,
            fixed_contact_weight=1000.0,
            temporal_laplacian_weight=40.0,
            body_relative_weight=10.0,
            q_prior_weight=0.02,
            q_smooth_weight=0.0,
            mesh_laplacian_weight=1.0,
            contact_laplacian_proxy_only=False,
            progress_callback=update_stage,
        )
        update_stage("saving_plan")
        generated_plan = replace(
            plan,
            status="generated",
            output_motion_path=str(result.output_motion_path),
            output_contact_layer=result.generation.output_contact_layer,
            output_segment_layer=result.generation.output_segment_layer,
        )
        write_contact_edit_plan(plan_path, generated_plan)
        generated_version_id = result.generation.output_motion_version_id
        if register_motion and generated_version_id and motion_asset_id:
            registered = read_motion_version(generated_version_id)
            metadata = dict(registered.metadata)
            metadata["parent_motion_id"] = parent_motion_version_id or motion_asset_id
            write_motion_version(
                MotionVersionRecord(
                    motion_version_id=registered.motion_version_id,
                    motion_path=registered.motion_path,
                    kind=registered.kind,
                    base_motion_id=registered.base_motion_id,
                    motion_asset_id=motion_asset_id,
                    parent_motion_version_id=parent_motion_version_id,
                    contact_layer=registered.contact_layer,
                    canonical_segment_path=registered.canonical_segment_path,
                    token_catalog_path=registered.token_catalog_path,
                    edit_plan_id=registered.edit_plan_id,
                    metadata=metadata,
                )
            )
        with state.generation_lock:
            state.generation.status = "succeeded"
            state.generation.stage = "complete"
            state.generation.output_motion_path = str(result.output_motion_path)
            state.generation.output_motion_id = result.generation.output_motion_version_id
            state.generation.warnings = list(result.warnings)
            state.generation.finished_at = time.time()
            state.overwrite = True
    except BaseException as exc:
        with state.generation_lock:
            state.generation.status = "failed"
            state.generation.stage = "failed"
            state.generation.error = str(exc)
            state.generation.finished_at = time.time()


def create_app(
    *,
    initial_motion_id: str | None = None,
    reset_recent_on_start: bool = False,
    generation_fn: Callable[..., ContactAwareGenerationResult] = apply_contact_aware_edit_plan_to_motion,
) -> FastAPI:
    app = FastAPI(title="Motion Edit Contact Editor")
    state = EditorState()
    app.state.editor_state = state
    app.mount("/repo", StaticFiles(directory=str(somaforge_root())), name="repo")

    @app.get("/api/motions")
    def motions() -> dict:
        return {
            "motions": [
                {
                    "motion_id": item.motion_id,
                    "label": item.motion_id,
                    "provenance": item.provenance,
                    "ready": Path(_repo_path(item.motion_path) or item.motion_path).exists(),
                }
                for item in _list_editor_motions()
            ]
        }

    @app.get("/api/recent-motions")
    def recent_motions() -> dict:
        return _recent_payload(state)

    @app.post("/api/session/load")
    def load(request: LoadRequest) -> dict:
        try:
            if state.generation_payload()["status"] == "running":
                raise ValueError("wait for the current generation job to finish before loading another motion")
            return _open_motion(state, request.motion_id)
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
        _require_editable(state)
        _require_generation_idle(state)
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

    @app.post("/api/session/move-handle")
    def move_handle(request: HandleMoveRequest) -> dict:
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        _require_editable(state)
        _require_generation_idle(state)
        try:
            graph = read_surface_editor_graph(state.session)
            handle = next(
                (item for item in _editor_contact_handles(graph.anchors) if item.handle_id == request.handle_id),
                None,
            )
            if handle is None:
                raise ValueError(f"contact episode handle not found: {request.handle_id}")
            requested = request.requested_world_position
            tangent = request.tangent_delta
            if request.target_uv is not None:
                tangent = [
                    float(request.target_uv[0]) - float(handle.surface_coordinates["u"]),
                    float(request.target_uv[1]) - float(handle.surface_coordinates["v"]),
                ]
                requested = None
            if requested is None and tangent is None:
                raise ValueError("move-handle requires requested_world_position, tangent_delta, or target_uv")
            before = state.snapshot()
            move_surface_editor_handle(
                state.session,
                handle_id=request.handle_id,
                requested_world_position=requested,
                tangent_delta=tangent,
                mode=request.mode,
                max_gap_frames=EDITOR_CONTACT_MAX_GAP_FRAMES,
                min_duration_frames=EDITOR_CONTACT_MIN_DURATION_FRAMES,
            )
            state.undo_stack.append(before)
            state.redo_stack.clear()
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/undo")
    def undo() -> dict:
        _require_editable(state)
        _require_generation_idle(state)
        if state.session is None or not state.undo_stack:
            raise HTTPException(status_code=409, detail="nothing to undo")
        state.redo_stack.append(state.snapshot())
        state.restore(state.undo_stack.pop())
        return _session_payload(state)

    @app.post("/api/session/redo")
    def redo() -> dict:
        _require_editable(state)
        _require_generation_idle(state)
        if state.session is None or not state.redo_stack:
            raise HTTPException(status_code=409, detail="nothing to redo")
        state.undo_stack.append(state.snapshot())
        state.restore(state.redo_stack.pop())
        return _session_payload(state)

    @app.post("/api/session/save")
    def save() -> dict:
        _require_editable(state)
        _require_generation_idle(state)
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            return _save_session(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/validate")
    def validate() -> dict:
        _require_editable(state)
        _require_generation_idle(state)
        try:
            return _save_session(state, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/restore-anchor")
    def restore_anchor(request: MoveRequest) -> dict:
        _require_editable(state)
        _require_generation_idle(state)
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

    @app.post("/api/session/restore-handle")
    def restore_handle(request: HandleMoveRequest) -> dict:
        _require_editable(state)
        _require_generation_idle(state)
        if state.session is None or state.initial_snapshot is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            original_graph, original_edits = state.initial_snapshot
            before = state.snapshot()
            restore_surface_editor_handle(
                state.session,
                handle_id=request.handle_id,
                initial_graph=original_graph,
                initial_edits=original_edits,
                max_gap_frames=EDITOR_CONTACT_MAX_GAP_FRAMES,
                min_duration_frames=EDITOR_CONTACT_MIN_DURATION_FRAMES,
            )
            state.undo_stack.append(before)
            state.redo_stack.clear()
            return _session_payload(state)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/reset")
    def reset() -> dict:
        _require_editable(state)
        _require_generation_idle(state)
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
        _require_generation_idle(state)
        if state.motion_id is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        try:
            return _open_motion(state, state.motion_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/session/settings")
    def settings(request: SettingsRequest) -> dict:
        _require_editable(state)
        _require_generation_idle(state)
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        state.session = replace(
            state.session,
            edit_plan_path=request.edit_plan_path or state.session.edit_plan_path,
            output_contact_layer=request.output_contact_layer or state.session.output_contact_layer,
        )
        _apply_generation_settings(state, request)
        return _session_payload(state)

    @app.get("/api/session/generation")
    def generation() -> dict:
        return state.generation_payload()

    @app.post("/api/session/generate", status_code=202)
    def generate(request: GenerateRequest) -> dict:
        if state.session is None:
            raise HTTPException(status_code=409, detail="no motion is loaded")
        _require_editable(state)
        with state.generation_lock:
            if state.generation.status == "running":
                raise HTTPException(status_code=409, detail="a generation job is already running")
        try:
            _apply_generation_settings(state, request)
            if not state.output_motion_path:
                raise ValueError("output motion path is required")
            if state.register_motion and not state.output_motion_id:
                raise ValueError("Motion ID is required when registration is enabled")
            output_path = Path(state.output_motion_path).expanduser()
            if output_path.exists() and not state.overwrite:
                raise FileExistsError(f"{output_path} already exists; enable Replace existing output to overwrite it")
            _save_session(state, validate=True)
            if not state.session.edit_plan_path:
                raise ValueError("ContactEditPlan path is required")
            worker_kwargs = {
                "state": state,
                "generation_fn": generation_fn,
                "plan_path": Path(state.session.edit_plan_path).expanduser(),
                "source_contact_layer": state.session.contact_layer,
                "output_contact_layer": state.session.output_contact_layer or "",
                "output_motion_path": state.output_motion_path,
                "output_segment_layer": state.output_segment_layer,
                "output_motion_id": state.output_motion_id,
                "register_motion": state.register_motion,
                "overwrite": state.overwrite,
                "fps": float(state.fps),
                "motion_asset_id": state.motion_asset_id,
                "parent_motion_version_id": state.motion_version_id,
                "force_source_motion_path": getattr(state.session, "contact_force_path", None),
            }
            worker = threading.Thread(
                target=_run_generation,
                kwargs=worker_kwargs,
                daemon=True,
                name="motion-edit-generate-ref",
            )
            with state.generation_lock:
                state.generation = GenerationJob(
                    status="running",
                    stage="queued",
                    output_motion_path=str(output_path),
                    output_motion_id=state.output_motion_id,
                    started_at=time.time(),
                )
                state.generation_worker = worker
            try:
                worker.start()
            except BaseException as exc:
                with state.generation_lock:
                    state.generation.status = "failed"
                    state.generation.stage = "failed"
                    state.generation.error = str(exc)
                    state.generation.finished_at = time.time()
                raise
            return state.generation_payload()
        except HTTPException:
            raise
        except Exception as exc:
            with state.generation_lock:
                if state.generation.status != "running":
                    state.generation = GenerationJob(
                        status="failed",
                        stage="preflight",
                        output_motion_path=state.output_motion_path,
                        output_motion_id=state.output_motion_id,
                        error=str(exc),
                        finished_at=time.time(),
                    )
                    state.generation_worker = None
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/")
    def index() -> FileResponse:
        target = WEB_DIST / "index.html"
        if not target.exists():
            raise HTTPException(status_code=503, detail="web frontend is not built; run npm run build in packages/motion_edit/web")
        return FileResponse(target)

    if WEB_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="web-assets")

    if reset_recent_on_start or initial_motion_id:
        @app.on_event("startup")
        def initialize_session() -> None:
            if reset_recent_on_start:
                clear_recent_motions()
            if initial_motion_id:
                _open_motion(state, initial_motion_id)
    return app


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", int(port))) != 0


def run_contact_editor(*, motion_id: str | None, host: str = "127.0.0.1", port: int = 8094, open_browser: bool = True) -> None:
    import uvicorn

    if not _port_available(port):
        raise RuntimeError(f"contact editor port {port} is already in use")
    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Motion Edit Contact Editor: {url}")
    uvicorn.run(
        create_app(
            initial_motion_id=motion_id,
            reset_recent_on_start=True,
        ),
        host=host,
        port=port,
        log_level="info",
    )
