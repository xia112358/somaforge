from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

from motion_edit.contact import append_anchor_edit_to_plan, read_contact_graph, write_contact_layer, write_contact_surfaces
from motion_edit.contact.actions import move_anchor_in_graph
from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.io import read_contact_surfaces, write_contact_jsonl
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactSurfaceRecord
from motion_edit.export import export_contact_overlay, export_surface_binding_overlay, export_surface_binding_report
from motion_edit.paths import LAYERS_ROOT, WORKBENCH_ROOT


@dataclass(frozen=True)
class SurfaceEditorSession:
    motion_path: str
    motion_id: str
    contact_layer: str
    surface_catalog: str | None
    session_name: str
    edit_plan_path: str | None
    output_contact_layer: str | None
    session_dir: Path
    overlay_path: Path
    report_path: Path
    contact_overlay_path: Path
    state_path: Path
    pending_edits_path: Path
    request_path: Path
    contact_layer_snapshot: Path

    def to_manifest(self) -> dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Path):
                data[key] = str(value)
        return data


def surface_session_dir(session_name: str, *, workbench_root: Path = WORKBENCH_ROOT) -> Path:
    return workbench_root / "surface_sessions" / session_name


def _read_surfaces(contact_layer: str, motion_id: str, surface_catalog: str | None, *, layers_root: Path) -> list[ContactSurfaceRecord]:
    if surface_catalog:
        return read_contact_surfaces(Path(surface_catalog).expanduser())
    sidecar = layers_root / contact_layer / "surfaces" / f"{motion_id}.jsonl"
    if sidecar.exists():
        return read_contact_surfaces(sidecar)
    return []


def _session_paths(
    *,
    motion_path: str,
    motion_id: str,
    contact_layer: str,
    surface_catalog: str | None,
    session_name: str,
    edit_plan_path: str | None,
    output_contact_layer: str | None,
    workbench_root: Path,
) -> SurfaceEditorSession:
    session_dir = surface_session_dir(session_name, workbench_root=workbench_root)
    return SurfaceEditorSession(
        motion_path=motion_path,
        motion_id=motion_id,
        contact_layer=contact_layer,
        surface_catalog=surface_catalog,
        session_name=session_name,
        edit_plan_path=edit_plan_path,
        output_contact_layer=output_contact_layer,
        session_dir=session_dir,
        overlay_path=session_dir / f"{motion_id}.surface_binding_overlay.json",
        report_path=session_dir / f"{motion_id}.surface_binding_report.json",
        contact_overlay_path=session_dir / f"{motion_id}.contact_overlay.json",
        state_path=session_dir / f"{motion_id}.surface_editor_state.json",
        pending_edits_path=session_dir / f"{motion_id}.pending_edits.jsonl",
        request_path=session_dir / f"{motion_id}.surface_editor_requests.jsonl",
        contact_layer_snapshot=session_dir / "contact_layer",
    )


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_session_files(session: SurfaceEditorSession, graph: ContactGraph, surfaces: list[ContactSurfaceRecord]) -> None:
    session.session_dir.mkdir(parents=True, exist_ok=True)
    write_contact_layer(session.contact_layer_snapshot, graph)
    if surfaces:
        write_contact_surfaces(session.contact_layer_snapshot / "surfaces" / f"{session.motion_id}.jsonl", surfaces)
    export_surface_binding_report(session.report_path, graph=graph, surfaces=surfaces)
    export_surface_binding_overlay(session.overlay_path, graph=graph, surfaces=surfaces)
    export_contact_overlay(session.contact_overlay_path, graph)
    _write_json(
        session.state_path,
        {
            **session.to_manifest(),
            "status": "prepared",
            "anchor_count": len(graph.anchors),
            "surface_count": len(surfaces),
            "processed_request_count": 0,
        },
    )
    _write_json(session.session_dir / "session.json", session.to_manifest())


def prepare_surface_editor_session(
    *,
    motion_path: str,
    motion_id: str,
    contact_layer: str,
    surface_catalog: str | None,
    session_name: str,
    edit_plan_path: str | None = None,
    output_contact_layer: str | None = None,
    layers_root: Path = LAYERS_ROOT,
    workbench_root: Path = WORKBENCH_ROOT,
) -> SurfaceEditorSession:
    graph = read_contact_graph(layers_root / contact_layer, motion_id)
    surfaces = _read_surfaces(contact_layer, motion_id, surface_catalog, layers_root=layers_root)
    session = _session_paths(
        motion_path=motion_path,
        motion_id=motion_id,
        contact_layer=contact_layer,
        surface_catalog=surface_catalog,
        session_name=session_name,
        edit_plan_path=edit_plan_path,
        output_contact_layer=output_contact_layer,
        workbench_root=workbench_root,
    )
    _write_session_files(session, graph, surfaces)
    return session


def read_surface_editor_session(path: str | Path) -> SurfaceEditorSession:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    path_fields = {
        "session_dir",
        "overlay_path",
        "report_path",
        "contact_overlay_path",
        "state_path",
        "pending_edits_path",
        "request_path",
        "contact_layer_snapshot",
    }
    if "request_path" not in data:
        session_dir = Path(data["session_dir"])
        data["request_path"] = session_dir / f"{data['motion_id']}.surface_editor_requests.jsonl"
    for field in path_fields:
        data[field] = Path(data[field])
    return SurfaceEditorSession(**data)


def _load_session_graph(session: SurfaceEditorSession) -> ContactGraph:
    return read_contact_graph(session.contact_layer_snapshot, session.motion_id)


def _load_session_surfaces(session: SurfaceEditorSession) -> list[ContactSurfaceRecord]:
    sidecar = session.contact_layer_snapshot / "surfaces" / f"{session.motion_id}.jsonl"
    if sidecar.exists():
        return read_contact_surfaces(sidecar)
    return []


def read_surface_editor_graph(session: SurfaceEditorSession) -> ContactGraph:
    return _load_session_graph(session)


def write_surface_editor_graph(session: SurfaceEditorSession, graph: ContactGraph) -> None:
    surfaces = _load_session_surfaces(session)
    write_contact_layer(session.contact_layer_snapshot, graph)
    export_surface_binding_report(session.report_path, graph=graph, surfaces=surfaces)
    export_surface_binding_overlay(session.overlay_path, graph=graph, surfaces=surfaces)
    export_contact_overlay(session.contact_overlay_path, graph)


def write_pending_surface_edits(session: SurfaceEditorSession, edits: Iterable[ContactAnchorEditRecord]) -> None:
    write_contact_jsonl(session.pending_edits_path, list(edits))


def move_surface_editor_anchor(
    session: SurfaceEditorSession,
    *,
    anchor_id: str,
    tangent_delta: Iterable[float] | None = None,
    requested_world_position: Iterable[float] | None = None,
    mode: str = "reject",
) -> tuple[ContactGraph, ContactAnchorEditRecord]:
    graph = _load_session_graph(session)
    moved_graph, edit = move_anchor_in_graph(
        graph,
        anchor_id=anchor_id,
        tangent_delta=tangent_delta,
        new_world_position=requested_world_position,
        mode=mode,
        source="viser_surface_editor",
    )
    edited_anchors = []
    for anchor in moved_graph.anchors:
        if anchor.anchor_id == anchor_id:
            metadata = dict(anchor.metadata)
            metadata["surface_editor_status"] = "edited"
            metadata["surface_editor_session"] = session.session_name
            edited_anchors.append(replace(anchor, metadata=metadata))
        else:
            edited_anchors.append(anchor)
    moved_graph = replace(moved_graph, anchors=edited_anchors, patches=patches_from_anchors(edited_anchors))
    write_surface_editor_graph(session, moved_graph)
    write_pending_surface_edits(session, [*read_pending_surface_edits(session), edit])
    return moved_graph, edit


def read_pending_surface_edits(session: SurfaceEditorSession) -> list[ContactAnchorEditRecord]:
    if not session.pending_edits_path.exists():
        return []
    records = json.loads("[" + ",".join(line for line in session.pending_edits_path.read_text(encoding="utf-8").splitlines() if line.strip()) + "]")
    return [ContactAnchorEditRecord(**record) for record in records]


def _delta3(before: list[float] | None, after: list[float] | None) -> list[float] | None:
    if before is None or after is None:
        return None
    return [float(after[index]) - float(before[index]) for index in range(3)]


def _delta_uv(before: dict | None, after: dict | None) -> list[float] | None:
    if not before or not after or "u" not in before or "v" not in before or "u" not in after or "v" not in after:
        return None
    return [float(after["u"]) - float(before["u"]), float(after["v"]) - float(before["v"])]


def coalesce_pending_surface_edits(session: SurfaceEditorSession) -> list[ContactAnchorEditRecord]:
    """Return one final edit per anchor, from initial touched position to final position."""
    coalesced: dict[str, ContactAnchorEditRecord] = {}
    order: list[str] = []
    for edit in read_pending_surface_edits(session):
        key = edit.anchor_id
        if key not in coalesced:
            order.append(key)
            coalesced[key] = edit
            continue
        first = coalesced[key]
        metadata = dict(first.metadata)
        metadata.update(edit.metadata)
        metadata["coalesced_pending_edits"] = int(metadata.get("coalesced_pending_edits", 1)) + 1
        old_world = first.old_world_position
        new_world = edit.new_world_position
        before_uv = first.surface_coordinates_before
        after_uv = edit.surface_coordinates_after
        coalesced[key] = replace(
            edit,
            old_world_position=old_world,
            new_world_position=new_world,
            delta_world=_delta3(old_world, new_world),
            tangent_delta=_delta_uv(before_uv, after_uv),
            surface_coordinates_before=before_uv,
            surface_coordinates_after=after_uv,
            source="viser_surface_editor",
            metadata=metadata,
        )
    return [coalesced[key] for key in order]


def append_surface_editor_request(
    session: SurfaceEditorSession,
    *,
    anchor_id: str,
    tangent_delta: Iterable[float] | None = None,
    requested_world_position: Iterable[float] | None = None,
    mode: str = "reject",
    source: str = "viser_ui",
) -> dict:
    existing = read_surface_editor_requests(session)
    request = {
        "kind": "move_anchor_request",
        "request_id": f"{session.motion_id}_surface_request_{len(existing):06d}",
        "anchor_id": anchor_id,
        "tangent_delta": list(tangent_delta) if tangent_delta is not None else None,
        "requested_world_position": list(requested_world_position) if requested_world_position is not None else None,
        "mode": mode,
        "source": source,
    }
    session.request_path.parent.mkdir(parents=True, exist_ok=True)
    with session.request_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(request, sort_keys=True) + "\n")
    return request


def read_surface_editor_requests(session: SurfaceEditorSession) -> list[dict]:
    if not session.request_path.exists():
        return []
    requests: list[dict] = []
    for line in session.request_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            requests.append(json.loads(line))
    return requests


def sync_surface_editor_requests(session: SurfaceEditorSession, *, save: bool = False, layers_root: Path = LAYERS_ROOT) -> tuple[int, Path | None]:
    state = json.loads(session.state_path.read_text(encoding="utf-8")) if session.state_path.exists() else {}
    processed = int(state.get("processed_request_count", 0))
    requests = read_surface_editor_requests(session)
    new_requests = requests[processed:]
    for request in new_requests:
        if request.get("kind") != "move_anchor_request":
            continue
        move_surface_editor_anchor(
            session,
            anchor_id=str(request["anchor_id"]),
            tangent_delta=request.get("tangent_delta"),
            requested_world_position=request.get("requested_world_position"),
            mode=str(request.get("mode", "reject")),
        )
    out = save_surface_editor_session(session, layers_root=layers_root) if save else None
    _write_json(
        session.state_path,
        {
            **session.to_manifest(),
            "status": "synced_saved" if save else "synced",
            "processed_request_count": len(requests),
            "applied_request_count": len(new_requests),
            "pending_edit_count": len(read_pending_surface_edits(session)),
            "output_contact_layer": session.output_contact_layer if save else None,
        },
    )
    return len(new_requests), out


def save_surface_editor_session(
    session: SurfaceEditorSession,
    *,
    output_contact_layer: str | None = None,
    edit_plan_path: str | None = None,
    layers_root: Path = LAYERS_ROOT,
) -> Path | None:
    destination = output_contact_layer or session.output_contact_layer
    graph = _load_session_graph(session)
    surfaces = _load_session_surfaces(session)
    out_layer: Path | None = None
    if destination:
        out_layer = write_contact_layer(layers_root / destination, graph)
        if surfaces:
            write_contact_surfaces(out_layer / "surfaces" / f"{session.motion_id}.jsonl", surfaces)
    plan_path = edit_plan_path or session.edit_plan_path
    if plan_path:
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
            append_anchor_edit_to_plan(
                plan_path,
                enriched,
                plan_id=Path(plan_path).stem,
                source_motion_path=session.motion_path,
                source_motion_id=session.motion_id,
                source_contact_layer=session.contact_layer,
            )
    _write_json(
        session.state_path,
        {
            **session.to_manifest(),
            "status": "saved",
            "output_contact_layer": destination,
            "pending_edit_count": len(read_pending_surface_edits(session)),
        },
    )
    return out_layer
