from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

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


def _body_color_hex(body: str | None) -> str:
    lowered = str(body or "").lower()
    for key, color in BODY_COLORS.items():
        if key in lowered or lowered in key:
            return "#{:02x}{:02x}{:02x}".format(*color)
    return "#55b4ff"


def _metadata_value(item: Any, key: str, default: Any = None) -> Any:
    meta = getattr(item, "metadata", None)
    if isinstance(meta, dict):
        return meta.get(key, default)
    return default


def _proto_boundaries(graph: Any, n_frames: int) -> list[dict[str, Any]]:
    by_frame: dict[int, dict[str, Any]] = {}
    for transition in getattr(graph, "transitions", []) or []:
        kind = str(_metadata_value(transition, "segmentation_kind", "transition") or "transition")
        stable_frames = _metadata_value(transition, "stable_anchor_frames", []) or []
        for frame in stable_frames:
            frame_i = int(max(0, min(n_frames - 1, int(frame))))
            entry = by_frame.setdefault(
                frame_i,
                {"frame": frame_i, "kind": "stable_contact_boundary", "sources": []},
            )
            entry["kind"] = "stable_contact_boundary"
            entry["sources"].append(getattr(transition, "transition_id", "transition"))
        for endpoint_kind, frame in (
            ("segment_start", getattr(transition, "start_frame", 0)),
            ("segment_end", getattr(transition, "end_frame", 0)),
        ):
            frame_i = int(max(0, min(n_frames - 1, int(frame))))
            entry = by_frame.setdefault(frame_i, {"frame": frame_i, "kind": endpoint_kind, "sources": []})
            if entry.get("kind") != "stable_contact_boundary":
                entry["kind"] = endpoint_kind if kind == "transition" else f"{kind}_{endpoint_kind}"
            entry["sources"].append(getattr(transition, "transition_id", "transition"))
    return [by_frame[frame] for frame in sorted(by_frame)]


def _transition_segments(graph: Any, n_frames: int) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for index, transition in enumerate(getattr(graph, "transitions", []) or []):
        start = int(max(0, min(n_frames, getattr(transition, "start_frame", 0))))
        end = int(max(start + 1, min(n_frames, getattr(transition, "end_frame", start + 1))))
        active_body = getattr(transition, "active_body", None)
        support_bodies = list(getattr(transition, "support_bodies", []) or [])
        segmentation_kind = str(_metadata_value(transition, "segmentation_kind", "transition") or "transition")
        endpoint_policy = str(_metadata_value(transition, "endpoint_policy", "") or "")
        touch = str(_metadata_value(transition, "touchdown_part", "") or "")
        label_parts = [segmentation_kind.replace("_", " ")]
        if active_body:
            label_parts.append(str(active_body))
        if touch:
            label_parts.append(f"touch {touch}")
        segments.append(
            {
                "segment_id": getattr(transition, "transition_id", f"segment_{index:04d}"),
                "start_frame": start,
                "end_frame": end,
                "active_body": active_body,
                "support_bodies": support_bodies,
                "transition_type": getattr(transition, "transition_type", "unknown"),
                "source_contact_point_id": getattr(transition, "source_anchor_id", None),
                "target_contact_point_id": getattr(transition, "target_anchor_id", None),
                "segmentation_kind": segmentation_kind,
                "endpoint_policy": endpoint_policy,
                "touchdown_part": touch,
                "owned_bodies": _metadata_value(transition, "owned_bodies", []),
                "stable_anchor_frames": _metadata_value(transition, "stable_anchor_frames", []),
                "color": _body_color_hex(active_body),
                "label": " · ".join(label_parts),
            }
        )
    return segments


def contact_timeline_state(
    *,
    controller: Any,
    playback: Any | None,
    motion_name: str,
    fps: int,
) -> dict[str, Any]:
    graph = controller.graph()
    n_frames = playback.n_frames if playback is not None else max(
        [0, *(int(anchor.end_frame) for anchor in getattr(graph, "anchors", []) or [])]
    ) + 1
    current_frame = playback.frame() if playback is not None else 0
    pending_edits = controller.pending_edits()
    bodies: list[str] = []
    contact_points: list[dict[str, Any]] = []
    selected_contact_point: dict[str, Any] | None = None
    status_counts: dict[str, int] = {}

    def _edit_value(edit: Any, key: str) -> Any:
        return edit.get(key) if isinstance(edit, dict) else getattr(edit, key, None)

    def _latest_edit(anchor_id: str) -> dict[str, Any] | None:
        for edit in reversed(pending_edits):
            if _edit_value(edit, "anchor_id") != anchor_id:
                continue
            return {
                "old_world_position": _edit_value(edit, "old_world_position"),
                "new_world_position": _edit_value(edit, "new_world_position"),
                "delta_world": _edit_value(edit, "delta_world"),
                "tangent_delta": _edit_value(edit, "tangent_delta"),
                "constraint_mode": _edit_value(edit, "constraint_mode"),
                "clamped": _edit_value(edit, "clamped"),
            }
        return None

    for anchor in getattr(graph, "anchors", []) or []:
        if anchor.body not in bodies:
            bodies.append(anchor.body)
        obj = controller._anchor_obj(anchor.anchor_id)
        status = str(obj.get("status") or "bound") if isinstance(obj, dict) else "bound"
        selected = anchor.anchor_id == controller.selected_anchor_id
        item = {
            "contact_point_id": anchor.anchor_id,
            "anchor_id": anchor.anchor_id,
            "body": anchor.body,
            "start_frame": int(anchor.start_frame),
            "end_frame": int(anchor.end_frame),
            "world_position": anchor.world_position,
            "surface_id": anchor.surface_id,
            "object_id": anchor.object_id,
            "surface_type": anchor.surface_type,
            "surface_coordinates": anchor.surface_coordinates,
            "surface_bounds": anchor.surface_bounds,
            "surface_binding_source": anchor.surface_binding_source,
            "failure_reason": anchor.metadata.get("surface_binding_failure_reason"),
            "patch_role": anchor.metadata.get("patch_role"),
            "status": status,
            "selected": selected,
            "warnings": obj.get("warnings", []) if isinstance(obj, dict) else [],
            "latest_edit": _latest_edit(anchor.anchor_id),
            "color": _body_color_hex(anchor.body),
        }
        status_counts[status] = status_counts.get(status, 0) + 1
        contact_points.append(item)
        if selected:
            selected_contact_point = item

    segments = _transition_segments(graph, int(n_frames))
    proto_boundaries = _proto_boundaries(graph, int(n_frames))
    segment_kinds: dict[str, int] = {}
    for segment in segments:
        kind = str(segment.get("segmentation_kind") or "transition")
        segment_kinds[kind] = segment_kinds.get(kind, 0) + 1

    session = getattr(getattr(controller, "state", None), "session", None)
    current_motion_name = motion_name
    layer_info: dict[str, str] = {}
    if session is not None:
        current_motion_name = str(getattr(session, "motion_path", motion_name)).split("/")[-1]
        layer_info = {
            "contact_layer": str(getattr(session, "contact_layer", "") or ""),
            "output_contact_layer": str(getattr(session, "output_contact_layer", "") or ""),
            "edit_plan_path": str(getattr(session, "edit_plan_path", "") or ""),
            "session_dir": str(getattr(session, "session_dir", "") or ""),
        }

    generation = getattr(getattr(controller, "state", None), "generation", None)
    generation_info = {
        "running": bool(getattr(generation, "running", False)) if generation is not None else False,
        "last_output_motion": getattr(generation, "last_output_motion", None) if generation is not None else None,
        "last_error": getattr(generation, "last_error", None) if generation is not None else None,
        "last_finished_at": getattr(generation, "last_finished_at", None) if generation is not None else None,
    }
    failed_count = status_counts.get("failed", 0)
    unbound_count = status_counts.get("unbound", 0)
    return {
        "schema_version": 6,
        "motion_name": current_motion_name,
        "n_frames": int(n_frames),
        "fps": int(fps),
        "current_frame": current_frame,
        "playing": bool(playback.playing["value"]) if playback is not None else False,
        "selected_anchor_id": controller.selected_anchor_id,
        "selected_contact_point_id": controller.selected_anchor_id,
        "pending_edit_count": len(pending_edits),
        "last_message": controller.state.last_message,
        "last_error": controller.state.last_error,
        "recent_motions": controller.recent_motion_items() if hasattr(controller, "recent_motion_items") else [],
        "bodies": bodies,
        "anchors": contact_points,
        "contact_points": contact_points,
        "segments": segments,
        "proto_boundaries": proto_boundaries,
        "selected_anchor": selected_contact_point,
        "selected_contact_point": selected_contact_point,
        "binding_counts": {
            "contact_point_count": len(contact_points),
            "anchor_count": len(contact_points),
            "segment_count": len(segments),
            "boundary_count": len(proto_boundaries),
            "bound_count": max(0, len(contact_points) - failed_count - unbound_count),
            "failed_count": failed_count,
            "unbound_count": unbound_count,
            "clamped_count": status_counts.get("clamped", 0),
            "low_confidence_count": status_counts.get("suspicious", 0),
        },
        "segment_counts": segment_kinds,
        "layers": layer_info,
        "generation": generation_info,
    }


def _editor_shell_css() -> str:
    return """
:root { color-scheme: dark; --bg:#070a10; --panel:#101723; --panel-2:#0b111b; --line:#27344d; --muted:#8fa1c3; --text:#e7edf9; --accent:#ffd45f; --green:#7ee08c; --red:#ff6b72; --orange:#ffad5c; --timeline-height:226px; }
html, body { margin:0; height:100%; background:var(--bg); color:var(--text); font-family:Inter, system-ui, sans-serif; overflow:hidden; }
#app { height:100%; display:grid; grid-template-rows:34px minmax(0,1fr) var(--timeline-height); }
#appbar { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:center; padding:0 10px; border-bottom:1px solid var(--line); background:#0d1420; box-sizing:border-box; }
#brand { display:flex; align-items:baseline; gap:12px; min-width:0; }
#title { font-size:15px; font-weight:700; white-space:nowrap; }
#motion-title { color:var(--muted); font:12px ui-monospace, monospace; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; user-select:text; }
#app-actions { display:flex; gap:8px; align-items:center; justify-content:flex-end; }
#pending-chip, #failed-chip { border:1px solid var(--line); border-radius:999px; background:#121b2a; color:#cdd9f0; padding:4px 8px; font:12px ui-monospace, monospace; white-space:nowrap; }
#pending-chip { border-color:rgba(255,212,95,.45); color:var(--accent); }
#failed-chip { display:none; border-color:rgba(255,107,114,.55); color:var(--red); }
#main { min-height:0; display:grid; grid-template-columns:260px minmax(0,1fr) 340px; background:#05070c; }
#left-panel, #inspector-panel { min-width:0; overflow:auto; background:var(--panel); border-right:1px solid var(--line); padding:10px; box-sizing:border-box; }
#inspector-panel { border-right:0; border-left:1px solid var(--line); }
#viewer-panel { position:relative; min-width:0; min-height:0; background:#05070c; overflow:hidden; }
#viewer { width:calc(100% + 250px); height:100%; border:0; background:#05070c; }
.viewport-hud { position:absolute; left:12px; top:10px; pointer-events:none; opacity:.68; }
.badge, .status-badge { border:1px solid var(--line); border-radius:999px; background:rgba(16,23,35,.88); color:#d7e2f5; padding:2px 7px; font-size:11px; white-space:nowrap; }
.status-badge.bound { color:#9bcfff; }
.status-badge.edited { border-color:rgba(126,224,140,.65); color:var(--green); }
.status-badge.failed { border-color:rgba(255,107,114,.7); color:var(--red); }
.status-badge.clamped, .status-badge.suspicious { border-color:rgba(255,173,92,.75); color:var(--orange); }
.card { border:1px solid var(--line); border-radius:7px; background:var(--panel-2); padding:10px; margin-bottom:10px; }
.card h3 { margin:0 0 8px; font-size:12px; color:#dbe6fa; display:flex; align-items:center; justify-content:space-between; gap:8px; }
.kv { display:grid; grid-template-columns:72px minmax(0,1fr); gap:6px 8px; font:12px Inter, system-ui, sans-serif; color:#c5d1e8; }
.kv .key { color:var(--muted); }
.kv .value { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-family:ui-monospace, monospace; }
.copyable { user-select:text; cursor:text; }
.copy-row { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:6px; align-items:center; }
.copy-btn { height:21px; padding:0 6px; font-size:10px; border-radius:4px; opacity:0; transition:opacity .12s ease; }
.copy-row:hover .copy-btn, .card:hover .copy-btn, .copy-btn:focus { opacity:.75; }
.event-card { border:1px solid #25324b; border-radius:6px; background:#0e1624; padding:7px; display:grid; gap:3px; }
.event-title { font-size:12px; color:#dce7ff; display:flex; align-items:center; justify-content:space-between; gap:6px; }
.event-meta { color:var(--muted); font:11px ui-monospace, monospace; overflow-wrap:anywhere; line-height:1.35; }
.mini-stats { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; }
.mini-stat { border:1px solid #25324b; border-radius:6px; background:#0e1624; padding:5px 7px; }
.mini-stat-label { color:var(--muted); font-size:10px; }
.mini-stat-value { color:#dce7ff; font:12px ui-monospace, monospace; }
.mini-stat.failed-active .mini-stat-value { color:var(--red); }
.mini-stat.clamped-active .mini-stat-value { color:var(--orange); }
.muted { color:var(--muted); }
.error { color:var(--red); }
select, button, input { height:28px; border:1px solid #34415f; border-radius:5px; background:#111a29; color:#dce7ff; padding:0 8px; box-sizing:border-box; }
button { cursor:pointer; }
button.primary { background:#1d5f8f; border-color:#2b8eca; color:white; }
button.danger { background:#67212a; border-color:#a33a45; color:#ffe9ed; }
button.ghost { background:#121927; }
button:disabled { opacity:.48; cursor:default; }
.stack { display:grid; gap:7px; }
.full { width:100%; }
#timeline-panel { min-height:0; border-top:1px solid var(--line); background:#0d1420; display:grid; grid-template-rows:36px minmax(0,1fr) 22px; }
#timeline-toolbar { display:grid; grid-template-columns:245px minmax(180px,1fr) auto; gap:10px; align-items:center; padding:4px 12px; border-bottom:1px solid #1e2a40; box-sizing:border-box; }
#timeline-title-group { display:flex; align-items:baseline; gap:10px; min-width:0; }
#timeline-title { font-size:12px; font-weight:650; color:#dce7ff; white-space:nowrap; }
#timeline-readout { color:var(--muted); font:11px ui-monospace, monospace; white-space:nowrap; }
#transport-controls { display:flex; gap:6px; align-items:center; justify-self:center; }
#contact-nav-controls { display:flex; gap:6px; align-items:center; justify-self:end; }
#frame-input { width:82px; font-family:ui-monospace, monospace; }
#timeline-scroll { min-height:0; overflow:hidden; }
#timeline { position:relative; width:100%; min-width:0; height:100%; background:#08101b; user-select:none; }
#frame-ruler { position:absolute; left:120px; right:16px; top:0; height:28px; border-bottom:1px solid #23304a; }
#track-area { position:absolute; left:0; right:0; top:28px; bottom:0; }
#playhead { position:absolute; top:0; bottom:0; width:2px; background:var(--accent); z-index:14; box-shadow:0 0 0 1px rgba(255,212,95,.24), 0 0 12px rgba(255,212,95,.18); }
#playhead-label { position:absolute; top:2px; transform:translateX(-50%); background:#231e0b; color:var(--accent); border:1px solid rgba(255,212,95,.38); border-radius:4px; padding:1px 5px; font:10px ui-monospace, monospace; z-index:15; }
.track-header { position:absolute; left:0; width:112px; height:24px; padding:5px 8px 0 0; box-sizing:border-box; text-align:right; color:#aab8d6; font:11px ui-monospace, monospace; border-right:1px solid #23304a; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; background:#08101b; z-index:5; }
.track-header.boundary-track { color:#ffe083; }
.track-line { position:absolute; left:120px; right:16px; height:1px; background:rgba(64,78,112,.35); }
.cutFrameMarker { position:absolute; top:3px; height:21px; width:2px; border-radius:2px; background:rgba(255,212,95,.72); z-index:4; cursor:pointer; box-shadow:0 0 8px rgba(255,212,95,.16); }
.cutFrameMarker.segment_start, .cutFrameMarker.segment_end { background:rgba(255,255,255,.42); box-shadow:none; }
.contactPointBlock { position:absolute; height:17px; border-radius:4px; opacity:.72; cursor:pointer; border:1px solid rgba(255,255,255,.18); box-sizing:border-box; }
.contactPointBlock:hover { opacity:1; transform:translateY(-1px); }
.contactPointBlock.selected { opacity:1; border-color:#ffe083; box-shadow:0 0 0 2px rgba(255,211,90,.42); z-index:6; }
.contactPointBlock.edited { border-color:var(--green); box-shadow:inset 0 -3px 0 rgba(126,224,140,.9); }
.contactPointBlock.failed { border-color:var(--red); background-image:repeating-linear-gradient(45deg,rgba(255,255,255,.18) 0 4px,transparent 4px 8px); }
.contactPointBlock.clamped, .contactPointBlock.suspicious { border-color:var(--orange); box-shadow:inset 0 -3px 0 rgba(255,173,92,.9); }
.tick { position:absolute; top:6px; color:#7184a8; font:10px ui-monospace, monospace; transform:translateX(-50%); }
.minorTick { position:absolute; top:18px; width:1px; height:8px; background:rgba(113,132,168,.45); }
#status-bar { display:flex; align-items:center; padding:0 12px; border-top:1px solid #1e2a40; color:#9fb0d0; font:11px ui-monospace, monospace; overflow:hidden; }
#status-left { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; user-select:text; }
"""


def _editor_shell_js() -> str:
    return r"""
const boot = BOOT_STATE;
document.getElementById('viewer').src = boot.viser_url;
let state = null;
let dragging = false;
let pendingFrame = null;
let pendingFrameTimer = null;
let lastFramePostMs = 0;
let framePostInFlight = false;
let playbackAnimId = null;
let playbackAnimMs = null;
let recentSignature = '';
const FRAME_POST_INTERVAL_MS = 50;
const timeline = document.getElementById('timeline');
const playhead = document.getElementById('playhead');
const playheadLabel = document.getElementById('playhead-label');
const recentSelect = document.getElementById('recent');
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function $(id) { return document.getElementById(id); }
function esc(value) { return String(value ?? '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch])); }
function attr(value) { return esc(value).replace(/'/g, '&#39;'); }
function copyButton(value, label='Copy') { return `<button class="copy-btn ghost" data-copy="${attr(value ?? '')}">${label}</button>`; }
function wireCopyButtons(root=document) {
  root.querySelectorAll('[data-copy]').forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      const text = button.getAttribute('data-copy') || '';
      navigator.clipboard?.writeText(text).then(() => {
        button.textContent = 'Copied';
        setTimeout(() => { button.textContent = 'Copy'; }, 800);
      }).catch(() => {
        const area = document.createElement('textarea');
        area.value = text;
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
      });
    };
  });
}
function railWidth() { return Math.max(1, timeline.clientWidth - 136); }
function railLeft() { return 120; }
function frameToX(frame) { return railLeft() + (frame / Math.max(1, state.n_frames - 1)) * railWidth(); }
function xToFrame(clientX) {
  const rect = timeline.getBoundingClientRect();
  const ratio = clamp((clientX - rect.left - railLeft()) / railWidth(), 0, 1);
  return Math.round(ratio * Math.max(0, state.n_frames - 1));
}
function shownFrame() { return Math.round(Number(state?.current_frame || 0)); }
function selectedContactPoint() { return state?.selected_contact_point || state?.selected_anchor || null; }
function cutFrames() {
  const frames = (state?.proto_boundaries || []).map(boundary => Number(boundary.frame)).filter(Number.isFinite);
  return Array.from(new Set(frames)).sort((a, b) => a - b);
}
function statusClass(status) { return String(status || 'bound').replace(/[^a-zA-Z0-9_-]/g, '_'); }
function kindClass(kind) { return String(kind || 'boundary').replace(/[^a-zA-Z0-9_-]/g, '_'); }
function shortContactPoint(point) {
  if (!point) return '-';
  return `${point.body || 'contact'} · ${point.start_frame ?? '-'}-${point.end_frame ?? '-'}`;
}
function vectorShort(value) {
  if (!Array.isArray(value)) return '';
  return value.map(v => Number(v).toFixed(3)).join(', ');
}
function eventFromMessage(message, kind='info') {
  const text = String(message || '');
  const bodyMatch = text.match(/anchor_(left_foot|right_foot|left_hand|right_hand)|(left_foot|right_foot|left_hand|right_hand)/);
  const body = bodyMatch?.find(Boolean) || 'contact point';
  const delta = text.match(/delta=\[([^\]]+)\]/);
  if (text.startsWith('moved ')) return {kind, title: `Moved ${body}`, body: delta ? `delta=(${delta[1]})` : text};
  return {kind, title: kind === 'error' ? 'Error' : 'Event', body: text};
}
function canGenerate() {
  const gen = state?.generation || {};
  return Boolean(state?.layers?.edit_plan_path) && !gen.running;
}
function updateTimelineHeight() {
  const tracks = Math.max(4, Number(state?.bodies?.length || 0) + 1);
  const height = Math.min(336, Math.max(218, 98 + tracks * 26));
  document.documentElement.style.setProperty('--timeline-height', `${height}px`);
}
function renderRecentMotions() {
  const items = state?.recent_motions || [];
  const signature = JSON.stringify(items.map(item => [item.label || '', item.motion_path || '', item.motion_id || '', item.contact_layer || '']));
  if (signature === recentSignature) return;
  if (document.activeElement === recentSelect && recentSelect.options.length > 0) return;
  const previous = recentSelect.value;
  recentSelect.innerHTML = '';
  items.forEach((item, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = item.label || item.motion_path || `motion ${index}`;
    recentSelect.appendChild(option);
  });
  if (previous && Number(previous) < recentSelect.options.length) recentSelect.value = previous;
  recentSignature = signature;
}
function syncPlaybackAnimation() {
  if (!state?.playing || dragging) {
    if (playbackAnimId !== null) cancelAnimationFrame(playbackAnimId);
    playbackAnimId = null;
    playbackAnimMs = null;
    return;
  }
  if (playbackAnimId !== null) return;
  playbackAnimMs = performance.now();
  playbackAnimId = requestAnimationFrame(localPlaybackTick);
}
function localPlaybackTick(now) {
  if (!state?.playing || dragging) { playbackAnimId = null; playbackAnimMs = null; return; }
  const maxFrame = Math.max(0, Number(state.n_frames || 1) - 1);
  const dt = playbackAnimMs === null ? 0 : Math.max(0, (now - playbackAnimMs) / 1000.0);
  playbackAnimMs = now;
  state.current_frame = Math.min(maxFrame, Number(state.current_frame || 0) + dt * Number(state.fps || 50));
  updateChrome();
  updatePlayhead();
  playbackAnimId = requestAnimationFrame(localPlaybackTick);
}
async function api(path, body) {
  const res = await fetch(path, {method: body ? 'POST' : 'GET', headers: {'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
  state = await res.json();
  render();
  return state;
}
async function refresh() { if (!dragging) await api('/api/state'); }
function setLocalFrame(frame) { if (!state) return; state.current_frame = clamp(frame, 0, Math.max(0, state.n_frames - 1)); updateChrome(); updatePlayhead(); }
async function postFrame(frame, commit=false) {
  if (framePostInFlight && !commit) return;
  framePostInFlight = true;
  try {
    const res = await fetch('/api/frame', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({frame})});
    const nextState = await res.json();
    state = nextState;
    if (dragging && !commit) { state.current_frame = frame; updateChrome(); updatePlayhead(); } else { render(); }
  } finally { framePostInFlight = false; }
}
function scheduleFramePost(frame, commit=false) {
  pendingFrame = frame;
  if (pendingFrameTimer !== null) clearTimeout(pendingFrameTimer);
  const now = performance.now();
  const wait = commit ? 0 : Math.max(0, FRAME_POST_INTERVAL_MS - (now - lastFramePostMs));
  pendingFrameTimer = setTimeout(() => {
    const frameToSend = pendingFrame;
    pendingFrame = null;
    pendingFrameTimer = null;
    lastFramePostMs = performance.now();
    postFrame(frameToSend, commit);
  }, wait);
}
function updateChrome() {
  if (!state) return;
  const frameText = `${shownFrame()} / ${Math.max(0, state.n_frames - 1)} · ${state.proto_boundaries?.length || 0} cut frames`;
  const gen = state.generation || {};
  const ready = canGenerate();
  $('timeline-readout').textContent = frameText;
  $('frame-input').value = shownFrame();
  $('play').textContent = state.playing ? 'Pause' : 'Play';
  $('motion-title').textContent = state.motion_name || '-';
  $('pending-chip').textContent = `pending ${state.pending_edit_count || 0}`;
  const failed = state.binding_counts?.failed_count || 0;
  $('failed-chip').textContent = `failed ${failed}`;
  $('failed-chip').style.display = failed ? 'inline-block' : 'none';
  const hint = 'Click cut-frame markers or contact point blocks · drag timeline to scrub';
  const message = state.last_message && state.last_message !== 'Ready' ? state.last_message : hint;
  $('status-left').textContent = state.last_error ? `Error: ${state.last_error}` : message;
  $('viewport-selected').textContent = shortContactPoint(selectedContactPoint());
  $('generate-top').disabled = !ready;
  $('generate-top').textContent = gen.running ? 'Generating...' : 'Generate';
  $('generate-top').title = ready ? 'Generate fullbody LTE from the current edit plan' : (gen.running ? 'Generation is running' : 'No editable contact plan is loaded');
}
function renderLeftPanel() {
  const counts = state.binding_counts || {};
  const layers = state.layers || {};
  const segKinds = Object.entries(state.segment_counts || {}).map(([k, v]) => `${k}:${v}`).join(' · ') || '-';
  renderRecentMotions();
  $('layer-summary').innerHTML = `
    <div class="kv">
      <div class="key">source</div><div class="copy-row"><div class="value copyable" title="${esc(layers.contact_layer)}">${esc(layers.contact_layer || '-')}</div>${copyButton(layers.contact_layer)}</div>
      <div class="key">output</div><div class="copy-row"><div class="value copyable" title="${esc(layers.output_contact_layer)}">${esc(layers.output_contact_layer || '-')}</div>${copyButton(layers.output_contact_layer)}</div>
      <div class="key">session</div><div class="copy-row"><div class="value copyable" title="${esc(layers.session_dir)}">${esc(layers.session_dir || '-')}</div>${copyButton(layers.session_dir)}</div>
    </div>`;
  const failedClass = Number(counts.failed_count || 0) > 0 ? ' failed-active' : '';
  const clampedClass = Number(counts.clamped_count || 0) > 0 ? ' clamped-active' : '';
  $('binding-summary').innerHTML = `
    <div class="mini-stats">
      <div class="mini-stat"><div class="mini-stat-label">contact points</div><div class="mini-stat-value">${counts.contact_point_count || counts.anchor_count || 0}</div></div>
      <div class="mini-stat"><div class="mini-stat-label">cut frames</div><div class="mini-stat-value">${counts.boundary_count || 0}</div></div>
      <div class="mini-stat"><div class="mini-stat-label">transitions</div><div class="mini-stat-value">${counts.segment_count || 0}</div></div>
      <div class="mini-stat"><div class="mini-stat-label">bound points</div><div class="mini-stat-value">${counts.bound_count || 0}</div></div>
      <div class="mini-stat${failedClass}"><div class="mini-stat-label">failed</div><div class="mini-stat-value">${counts.failed_count || 0}</div></div>
      <div class="mini-stat${clampedClass}"><div class="mini-stat-label">clamped</div><div class="mini-stat-value">${counts.clamped_count || 0}</div></div>
      <div class="mini-stat"><div class="mini-stat-label">transition kind</div><div class="mini-stat-value" title="${esc(segKinds)}">${esc(segKinds)}</div></div>
    </div>`;
  wireCopyButtons($('layer-summary'));
}
function renderInspector() {
  const p = selectedContactPoint();
  if (!p) {
    $('selected-anchor-card').innerHTML = '<h3>Selected Contact Point</h3><div class="muted">No contact point selected.</div>';
    $('surface-card').innerHTML = '<h3>Surface Binding</h3><div class="muted">Select a contact point.</div>';
    $('edit-card').innerHTML = '<h3>Edit</h3><div class="muted">Drag a contact point in the 3D viewport to edit.</div>';
    return;
  }
  $('selected-anchor-card').innerHTML = `
    <h3>Selected Contact Point <span class="status-badge ${statusClass(p.status)}">${esc(p.status || 'bound')}</span></h3>
    <div class="kv">
      <div class="key">id</div><div class="copy-row"><div class="value copyable" title="${esc(p.contact_point_id)}">${esc(p.contact_point_id)}</div>${copyButton(p.contact_point_id)}</div>
      <div class="key">body</div><div class="value">${esc(p.body)}</div>
      <div class="key">frames</div><div class="value">${p.start_frame} - ${p.end_frame}</div>
      <div class="key">patch</div><div class="value">${esc(p.patch_role || '-')}</div>
      <div class="key">world</div><div class="value" title="${esc(vectorShort(p.world_position))}">${esc(vectorShort(p.world_position) || '-')}</div>
    </div>`;
  $('surface-card').innerHTML = `
    <h3>Surface Binding</h3>
    <div class="kv">
      <div class="key">surface</div><div class="copy-row"><div class="value copyable" title="${esc(p.surface_id)}">${esc(p.surface_id || '-')}</div>${copyButton(p.surface_id)}</div>
      <div class="key">object</div><div class="value">${esc(p.object_id || '-')}</div>
      <div class="key">type</div><div class="value">${esc(p.surface_type || '-')}</div>
      <div class="key">uv</div><div class="value">${esc(p.surface_coordinates ? JSON.stringify(p.surface_coordinates) : '-')}</div>
      <div class="key">reason</div><div class="value error">${esc(p.failure_reason || '')}</div>
    </div>`;
  const edit = p.latest_edit;
  $('edit-card').innerHTML = edit ? `
    <h3>Contact Edit</h3><div class="kv">
      <div class="key">delta</div><div class="value">${esc(vectorShort(edit.delta_world) || '-')}</div>
      <div class="key">tangent</div><div class="value">${esc(vectorShort(edit.tangent_delta) || '-')}</div>
      <div class="key">mode</div><div class="value">${esc(edit.constraint_mode || '-')}</div>
      <div class="key">clamped</div><div class="value">${edit.clamped ? 'yes' : 'no'}</div>
    </div>` : '<h3>Contact Edit</h3><div class="muted">No pending edit for selected contact point.</div>';
  wireCopyButtons($('selected-anchor-card'));
  wireCopyButtons($('surface-card'));
}
function renderGenerationCard() {
  const gen = state.generation || {};
  $('generation-card').innerHTML = `
    <h3>Generation</h3>
    <div class="kv">
      <div class="key">status</div><div class="value">${gen.running ? 'running' : 'idle'}</div>
      <div class="key">output</div><div class="copy-row"><div class="value copyable" title="${esc(gen.last_output_motion)}">${esc(gen.last_output_motion || '-')}</div>${copyButton(gen.last_output_motion)}</div>
      <div class="key">error</div><div class="value error">${esc(gen.last_error || '')}</div>
    </div>`;
  wireCopyButtons($('generation-card'));
}
function renderWarnings() {
  const events = [];
  if (state.last_error) events.push(eventFromMessage(state.last_error, 'error'));
  if (state.last_message && state.last_message !== 'Ready') events.push(eventFromMessage(state.last_message, 'info'));
  (state.contact_points || state.anchors || []).filter(p => (p.warnings || []).length || p.failure_reason).slice(0, 5).forEach(p => {
    events.push({kind: 'warning', title: `${p.body} ${p.status}`, body: p.failure_reason || (p.warnings || []).join('; ')});
  });
  $('warning-list').innerHTML = events.length ? events.map(ev => `
    <div class="event-card"><div class="event-title"><span>${esc(ev.title)}</span></div><div class="event-meta">${esc(ev.body)}</div></div>`).join('') : '<div class="muted">No recent events.</div>';
}
function updatePlayhead() {
  if (!state) return;
  const x = frameToX(shownFrame());
  playhead.style.left = x + 'px';
  playheadLabel.style.left = x + 'px';
  playheadLabel.textContent = shownFrame();
}
function renderTimeline() {
  const frameRuler = $('frame-ruler');
  const trackArea = $('track-area');
  frameRuler.innerHTML = '';
  trackArea.innerHTML = '';
  const maxFrame = Math.max(0, state.n_frames - 1);
  const major = Math.max(1, Math.ceil(maxFrame / 8));
  for (let frame = 0; frame <= maxFrame; frame += major) {
    const x = frameToX(frame);
    const tick = document.createElement('div');
    tick.className = 'tick';
    tick.style.left = x + 'px';
    tick.textContent = frame;
    frameRuler.appendChild(tick);
    const minor = document.createElement('div');
    minor.className = 'minorTick';
    minor.style.left = x + 'px';
    frameRuler.appendChild(minor);
  }
  const laneH = 26;
  const boundaryTop = 2;
  const bodyTop = 32;
  const boundaryHeader = document.createElement('div');
  boundaryHeader.className = 'track-header boundary-track';
  boundaryHeader.style.top = boundaryTop + 'px';
  boundaryHeader.textContent = 'cut frames';
  trackArea.appendChild(boundaryHeader);
  const boundaryLine = document.createElement('div');
  boundaryLine.className = 'track-line';
  boundaryLine.style.top = (boundaryTop + laneH - 1) + 'px';
  trackArea.appendChild(boundaryLine);
  (state.proto_boundaries || []).forEach(boundary => {
    const x = frameToX(boundary.frame);
    const marker = document.createElement('div');
    marker.className = 'cutFrameMarker ' + kindClass(boundary.kind);
    marker.style.left = x + 'px';
    marker.title = `cut frame ${boundary.frame}\n${boundary.kind}\n${(boundary.sources || []).join(', ')}`;
    marker.onclick = event => { event.stopPropagation(); api('/api/frame', {frame: boundary.frame}); };
    trackArea.appendChild(marker);
  });
  const bodies = state.bodies || [];
  bodies.forEach((body, i) => {
    const y = bodyTop + i * laneH;
    const header = document.createElement('div');
    header.className = 'track-header';
    header.style.top = y + 'px';
    header.textContent = body;
    trackArea.appendChild(header);
    const line = document.createElement('div');
    line.className = 'track-line';
    line.style.top = (y + laneH - 1) + 'px';
    trackArea.appendChild(line);
  });
  (state.contact_points || state.anchors || []).forEach(point => {
    const lane = Math.max(0, bodies.indexOf(point.body));
    const start = clamp(point.start_frame, 0, Math.max(0, state.n_frames - 1));
    const end = clamp(point.end_frame, start + 1, state.n_frames);
    const el = document.createElement('div');
    el.className = 'contactPointBlock ' + statusClass(point.status) + (point.selected ? ' selected' : '');
    el.style.left = frameToX(start) + 'px';
    el.style.width = Math.max(3, frameToX(end - 1) - frameToX(start)) + 'px';
    el.style.top = (bodyTop + lane * laneH + 4) + 'px';
    el.style.background = point.color || '#55b4ff';
    el.title = `${point.contact_point_id || point.anchor_id}\n${point.body} ${point.start_frame}-${point.end_frame}\ncontact point / handle\n${point.surface_id || ''}\n${point.status || ''}`;
    el.onclick = event => { event.stopPropagation(); api('/api/select_anchor', {anchor_id: point.anchor_id || point.contact_point_id, frame: point.start_frame}); };
    trackArea.appendChild(el);
  });
  updatePlayhead();
}
function render() {
  if (!state) return;
  updateTimelineHeight();
  updateChrome();
  renderLeftPanel();
  renderInspector();
  renderGenerationCard();
  renderWarnings();
  renderTimeline();
  syncPlaybackAnimation();
}
function scrub(event, commit=false) { const frame = xToFrame(event.clientX); setLocalFrame(frame); scheduleFramePost(frame, commit); }
timeline.addEventListener('pointerdown', event => { dragging = true; timeline.setPointerCapture(event.pointerId); scrub(event); syncPlaybackAnimation(); });
timeline.addEventListener('pointermove', event => { if (dragging) scrub(event); });
timeline.addEventListener('pointerup', event => { if (dragging) scrub(event, true); dragging = false; syncPlaybackAnimation(); });
timeline.addEventListener('pointercancel', event => { if (dragging) scrub(event, true); dragging = false; syncPlaybackAnimation(); });
$('play').onclick = () => api('/api/play', {playing: !state.playing});
$('frame-input').onchange = () => api('/api/frame', {frame: Number($('frame-input').value || 0)});
$('snap-selected').onclick = () => { const p = selectedContactPoint(); if (p) api('/api/frame', {frame: p.start_frame}); };
$('prev-cut').onclick = () => selectRelativeCutFrame(-1);
$('next-cut').onclick = () => selectRelativeCutFrame(1);
$('prev-contact').onclick = () => selectRelativeContactPoint(-1);
$('next-contact').onclick = () => selectRelativeContactPoint(1);
$('generate-top').onclick = () => api('/api/generate', {});
recentSelect.onchange = () => api('/api/open_recent', {index: Number(recentSelect.value || 0)});
$('load-motion').onclick = () => api('/api/load_motion', {});
$('discard').onclick = () => api('/api/discard', {});
function selectRelativeCutFrame(offset) {
  const frames = cutFrames();
  if (!frames.length) return;
  const frame = shownFrame();
  let next;
  if (offset > 0) {
    next = frames.find(value => value > frame);
    if (next === undefined) next = frames[0];
  } else {
    next = frames.slice().reverse().find(value => value < frame);
    if (next === undefined) next = frames[frames.length - 1];
  }
  api('/api/frame', {frame: next});
}
function selectRelativeContactPoint(offset) {
  const points = state?.contact_points || state?.anchors || [];
  if (!points.length) return;
  const ids = points.map(p => p.contact_point_id || p.anchor_id);
  const current = Math.max(0, ids.indexOf(state.selected_contact_point_id || state.selected_anchor_id));
  const next = points[(current + offset + points.length) % points.length];
  api('/api/select_anchor', {anchor_id: next.anchor_id || next.contact_point_id, frame: next.start_frame});
}
window.addEventListener('keydown', event => {
  if (!state) return;
  if (event.code === 'Space') { event.preventDefault(); api('/api/play', {playing: !state.playing}); }
  if (event.code === 'ArrowLeft') api('/api/frame', {frame: shownFrame() - (event.shiftKey ? 10 : 1)});
  if (event.code === 'ArrowRight') api('/api/frame', {frame: shownFrame() + (event.shiftKey ? 10 : 1)});
});
window.addEventListener('resize', () => { if (state) renderTimeline(); });
refresh();
setInterval(refresh, 500);
"""


def _timeline_html(*, viser_url: str) -> str:
    state_json = json.dumps({"viser_url": viser_url})
    script = _editor_shell_js().replace("BOOT_STATE", state_json)
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Motion Edit Contact Editor</title>
<style>{_editor_shell_css()}</style>
</head>
<body>
<div id="app">
  <header id="appbar">
    <div id="brand"><div id="title">Motion Edit</div><div id="motion-title"></div></div>
    <div id="app-actions">
      <span id="pending-chip">pending 0</span>
      <span id="failed-chip">failed 0</span>
      <button id="discard" class="danger">Discard</button>
      <button id="generate-top" class="primary" disabled title="No editable contact plan is loaded.">Generate</button>
    </div>
  </header>
  <main id="main">
    <aside id="left-panel">
      <section class="card"><h3>Motion</h3><div class="stack"><select id="recent" class="full"></select><button id="load-motion" class="primary">Load Motion...</button></div></section>
      <section class="card"><h3>Layers</h3><div id="layer-summary"></div></section>
      <section class="card"><h3>Timeline Objects</h3><div id="binding-summary"></div></section>
      <section class="card"><h3>Events / Warnings</h3><div id="warning-list"></div></section>
    </aside>
    <section id="viewer-panel">
      <iframe id="viewer"></iframe>
      <div class="viewport-hud"><span id="viewport-selected" class="badge">no contact point</span></div>
    </section>
    <aside id="inspector-panel">
      <section id="selected-anchor-card" class="card"></section>
      <section id="surface-card" class="card"></section>
      <section id="edit-card" class="card"></section>
      <section id="generation-card" class="card"></section>
    </aside>
  </main>
  <section id="timeline-panel">
    <div id="timeline-toolbar">
      <div id="timeline-title-group"><div id="timeline-title">Contact Sequencer</div><div id="timeline-readout">-</div></div>
      <div id="transport-controls">
        <button id="play" class="primary">Play</button>
        <input id="frame-input" type="number" min="0" value="0" aria-label="Current frame" title="Current frame" />
      </div>
      <div id="contact-nav-controls">
        <button id="snap-selected" class="ghost">Go to selected contact</button>
        <button id="prev-cut" class="ghost">Prev cut</button>
        <button id="next-cut" class="ghost">Next cut</button>
        <button id="prev-contact" class="ghost">Prev contact</button>
        <button id="next-contact" class="ghost">Next contact</button>
      </div>
    </div>
    <div id="timeline-scroll"><div id="timeline"><div id="frame-ruler"></div><div id="track-area"></div><div id="playhead"></div><div id="playhead-label"></div></div></div>
    <div id="status-bar"><div id="status-left">Ready</div></div>
  </section>
</div>
<script>{script}</script>
</body>
</html>"""


def start_contact_timeline_wrapper(
    *,
    controller: Any,
    playback: Any | None,
    timeline_port: int,
    viser_port: int,
    motion_name: str,
    fps: int,
) -> ThreadingHTTPServer:
    viser_url = f"http://localhost:{viser_port}"

    def state() -> dict[str, Any]:
        return contact_timeline_state(controller=controller, playback=playback, motion_name=motion_name, fps=fps)

    def target_controller() -> Any:
        return getattr(controller, "current", None) or controller

    def generation_state(target: Any) -> Any:
        state_obj = getattr(target, "state", None)
        if state_obj is None:
            return SimpleNamespace(running=False, last_output_motion=None, last_error="no editor state", last_started_at=None, last_finished_at=None)
        gen = getattr(state_obj, "generation", None)
        if gen is None:
            gen = SimpleNamespace(running=False, last_output_motion=None, last_error=None, last_started_at=None, last_finished_at=None)
            setattr(state_obj, "generation", gen)
        return gen

    def start_generation() -> None:
        target = target_controller()
        state_obj = getattr(target, "state", None)
        session = getattr(state_obj, "session", None)
        gen = generation_state(target)
        if session is None:
            if state_obj is not None:
                state_obj.last_error = "load a motion before generating"
            return
        if bool(getattr(gen, "running", False)):
            state_obj.last_error = "generation already running"
            return

        def set_status(message: str, *, error: bool = False) -> None:
            if error:
                state_obj.last_error = message
            else:
                state_obj.last_error = None
                state_obj.last_message = message

        try:
            from motion_edit.viewer.contact_editor.app import (
                _avoid_generation_output_collision,
                _default_generation_outputs,
                _generate_fullbody_lte_from_session,
                _recent_entry_from_generated_session,
            )
            from motion_edit.workbench.recent import upsert_recent_motion
        except Exception as exc:
            set_status(f"generation backend unavailable: {exc}", error=True)
            return

        defaults = _default_generation_outputs(session)
        inputs = _avoid_generation_output_collision(
            {
                "generated_motion": defaults["output_motion"],
                "generated_contact_layer": defaults["output_contact_layer"],
                "generated_segment_layer": defaults["output_segment_layer"],
                "generated_motion_version_id": defaults["output_motion_version_id"],
                "intermediate_dir": defaults["intermediate_dir"],
                "overwrite": False,
                "register_motion_version": False,
            }
        )
        gen.running = True
        gen.last_error = None
        gen.last_output_motion = inputs["generated_motion"]
        gen.last_started_at = time.time()
        set_status(f"generate fullbody LTE started: {inputs['generated_motion']}")

        def worker() -> None:
            try:
                result = _generate_fullbody_lte_from_session(
                    session,
                    output_motion=inputs["generated_motion"],
                    output_motion_version_id=inputs["generated_motion_version_id"],
                    output_contact_layer=inputs["generated_contact_layer"],
                    output_segment_layer=inputs["generated_segment_layer"],
                    intermediate_dir=inputs["intermediate_dir"],
                    dry_run=False,
                    overwrite=inputs["overwrite"],
                    register_motion_version=inputs["register_motion_version"],
                )
                generated_entry = _recent_entry_from_generated_session(
                    session,
                    output_motion=str(result.output_motion_path),
                    output_contact_layer=inputs["generated_contact_layer"],
                    output_segment_layer=inputs["generated_segment_layer"],
                    output_motion_version_id=inputs["generated_motion_version_id"],
                    terrain_urdf=getattr(target, "terrain_urdf", None),
                )
                upsert_recent_motion(generated_entry)
                if callable(getattr(target, "reload_motion_callback", None)):
                    target.reload_motion_callback(generated_entry)
                warning_suffix = f" warnings={len(result.warnings or [])}" if result.warnings else ""
                gen.last_output_motion = str(result.output_motion_path)
                gen.last_error = None
                set_status(f"generated fullbody LTE: {result.output_motion_path}{warning_suffix}")
            except Exception as exc:
                gen.last_error = str(exc)
                set_status(f"generate fullbody LTE failed: {exc}", error=True)
            finally:
                gen.running = False
                gen.last_finished_at = time.time()

        threading.Thread(target=worker, daemon=True).start()

    class TimelineHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any]) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict[str, Any]:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802
            if urlparse(self.path).path == "/api/state":
                self._send_json(state())
                return
            html = _timeline_html(viser_url=viser_url).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def do_POST(self) -> None:  # noqa: N802
            body = self._read_json()
            path = urlparse(self.path).path
            try:
                if path == "/api/frame" and playback is not None:
                    playback.set_frame(int(body.get("frame", playback.frame())))
                elif path == "/api/play" and playback is not None:
                    playback.playing["value"] = bool(body.get("playing", not playback.playing["value"]))
                elif path == "/api/select_anchor":
                    anchor_id = str(body.get("anchor_id") or "")
                    controller.select_anchor(anchor_id)
                    if playback is not None and "frame" in body:
                        playback.set_frame(int(body["frame"]))
                elif path == "/api/save":
                    controller.save()
                elif path == "/api/generate":
                    start_generation()
                elif path == "/api/discard":
                    controller.discard()
                elif path == "/api/open_recent":
                    controller.open_recent_motion(int(body.get("index", 0)))
                elif path == "/api/load_motion":
                    if hasattr(controller, "open_load_dialog"):
                        controller.open_load_dialog()
                    else:
                        controller.state.last_error = "load dialog unavailable"
                elif path == "/api/open_latest":
                    if hasattr(controller, "open_latest_generated_motion"):
                        controller.open_latest_generated_motion()
                    else:
                        controller.state.last_error = "open latest unavailable"
                elif path == "/api/reload_motion":
                    if hasattr(controller, "reload_motion"):
                        controller.reload_motion()
                    else:
                        controller.state.last_error = "reload unavailable"
            except Exception as exc:  # pragma: no cover - defensive UI path
                controller.state.last_error = str(exc)
            self._send_json(state())

        def log_message(self, _format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("localhost", int(timeline_port)), TimelineHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
