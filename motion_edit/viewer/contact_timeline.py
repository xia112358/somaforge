from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def _body_color_hex(body: str) -> str:
    lowered = body.lower()
    for key, color in BODY_COLORS.items():
        if key in lowered or lowered in key:
            return "#{:02x}{:02x}{:02x}".format(*color)
    return "#55b4ff"


def contact_timeline_state(
    *,
    controller: Any,
    playback: Any | None,
    motion_name: str,
    fps: int,
) -> dict[str, Any]:
    graph = controller.graph()
    n_frames = playback.n_frames if playback is not None else max((anchor.end_frame for anchor in graph.anchors), default=0) + 1
    current_frame = playback.frame() if playback is not None else 0
    anchors = []
    bodies: list[str] = []
    status_counts: dict[str, int] = {}
    selected_anchor: dict[str, Any] | None = None
    pending_edits = controller.pending_edits()

    def _edit_value(edit: Any, key: str) -> Any:
        if isinstance(edit, dict):
            return edit.get(key)
        return getattr(edit, key, None)

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

    for anchor in graph.anchors:
        if anchor.body not in bodies:
            bodies.append(anchor.body)
        status = "selected" if anchor.anchor_id == controller.selected_anchor_id else "bound"
        obj = controller._anchor_obj(anchor.anchor_id)
        if obj is not None:
            status = str(obj.get("status") or status)
            if anchor.anchor_id == controller.selected_anchor_id:
                status = "selected"
        warnings = obj.get("warnings", []) if isinstance(obj, dict) else []
        latest_edit = _latest_edit(anchor.anchor_id)
        item = {
            "anchor_id": anchor.anchor_id,
            "body": anchor.body,
            "start_frame": anchor.start_frame,
            "end_frame": anchor.end_frame,
            "world_position": anchor.world_position,
            "surface_id": anchor.surface_id,
            "object_id": anchor.object_id,
            "surface_type": anchor.surface_type,
            "surface_coordinates": anchor.surface_coordinates,
            "surface_bounds": anchor.surface_bounds,
            "surface_binding_source": anchor.surface_binding_source,
            "failure_reason": anchor.metadata.get("surface_binding_failure_reason"),
            "status": status,
            "warnings": warnings,
            "latest_edit": latest_edit,
            "color": _body_color_hex(anchor.body),
        }
        status_counts[status] = status_counts.get(status, 0) + 1
        anchors.append(item)
        if anchor.anchor_id == controller.selected_anchor_id:
            selected_anchor = item
    current_motion_name = motion_name
    session = getattr(getattr(controller, "state", None), "session", None)
    if session is not None:
        current_motion_name = str(getattr(session, "motion_path", motion_name)).split("/")[-1]
    layer_info = {}
    if session is not None:
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
    return {
        "schema_version": 1,
        "motion_name": current_motion_name,
        "n_frames": n_frames,
        "fps": int(fps),
        "current_frame": current_frame,
        "playing": bool(playback.playing["value"]) if playback is not None else False,
        "selected_anchor_id": controller.selected_anchor_id,
        "pending_edit_count": len(controller.pending_edits()),
        "last_message": controller.state.last_message,
        "last_error": controller.state.last_error,
        "recent_motions": controller.recent_motion_items() if hasattr(controller, "recent_motion_items") else [],
        "bodies": bodies,
        "anchors": anchors,
        "selected_anchor": selected_anchor,
        "binding_counts": {
            "anchor_count": len(anchors),
            "bound_count": status_counts.get("bound", 0) + status_counts.get("selected", 0) + status_counts.get("edited", 0),
            "failed_count": status_counts.get("failed", 0),
            "unbound_count": status_counts.get("unbound", 0),
            "clamped_count": status_counts.get("clamped", 0),
            "low_confidence_count": status_counts.get("suspicious", 0),
        },
        "layers": layer_info,
        "generation": generation_info,
    }


def _editor_shell_css() -> str:
    return """
:root {
  color-scheme: dark;
  --bg: #070a10;
  --panel: #101723;
  --panel-2: #0b111b;
  --panel-3: #151d2b;
  --line: #27344d;
  --muted: #8fa1c3;
  --text: #e7edf9;
  --accent: #ffd45f;
  --green: #7ee08c;
  --red: #ff6b72;
  --orange: #ffad5c;
}
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); font-family: Inter, system-ui, sans-serif; overflow: hidden; }
#app { height: 100%; display: grid; grid-template-rows: 42px minmax(0, 1fr) 310px; background: var(--bg); }
#appbar { display: grid; grid-template-columns: 340px minmax(0, 1fr) 430px; gap: 12px; align-items: center; padding: 0 12px; border-bottom: 1px solid var(--line); background: #0d1420; box-sizing: border-box; }
#brand { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
#title { font-size: 15px; font-weight: 700; white-space: nowrap; }
#motion-title { color: var(--muted); font: 12px ui-monospace, monospace; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
#transport, #app-actions { display: flex; gap: 8px; align-items: center; justify-content: center; min-width: 0; }
#app-actions { justify-content: flex-end; }
#frame-chip, #pending-chip { border: 1px solid var(--line); border-radius: 5px; background: #121b2a; color: #cdd9f0; padding: 5px 8px; font: 12px ui-monospace, monospace; white-space: nowrap; }
#main { min-height: 0; display: grid; grid-template-columns: 260px minmax(0, 1fr) 340px; background: #05070c; }
#left-panel, #inspector-panel { min-width: 0; overflow: auto; background: var(--panel); border-right: 1px solid var(--line); padding: 10px; box-sizing: border-box; }
#inspector-panel { border-right: 0; border-left: 1px solid var(--line); }
#viewer-panel { position: relative; min-width: 0; min-height: 0; background: #05070c; }
#viewer { width: 100%; height: 100%; border: 0; background: #05070c; }
.viewport-hud { position: absolute; left: 12px; top: 10px; display: flex; gap: 8px; pointer-events: none; }
.badge, .status-badge { border: 1px solid var(--line); border-radius: 999px; background: rgba(16, 23, 35, .88); color: #d7e2f5; padding: 3px 8px; font-size: 11px; white-space: nowrap; }
.status-badge.edited { border-color: rgba(126, 224, 140, .65); color: var(--green); }
.status-badge.failed { border-color: rgba(255, 107, 114, .7); color: var(--red); }
.status-badge.clamped, .status-badge.suspicious { border-color: rgba(255, 173, 92, .75); color: var(--orange); }
.card { border: 1px solid var(--line); border-radius: 7px; background: var(--panel-2); padding: 10px; margin-bottom: 10px; }
.card h3 { margin: 0 0 8px; font-size: 12px; letter-spacing: 0; color: #dbe6fa; }
.kv { display: grid; grid-template-columns: 88px minmax(0, 1fr); gap: 5px 8px; font: 12px ui-monospace, monospace; color: #c5d1e8; }
.kv .key { color: var(--muted); }
.kv .value { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.muted { color: var(--muted); }
.warn { color: var(--orange); }
.error { color: var(--red); }
select, button, input { height: 28px; border: 1px solid #34415f; border-radius: 5px; background: #111a29; color: #dce7ff; padding: 0 8px; box-sizing: border-box; }
button { cursor: pointer; }
button.primary { background: #1d5f8f; border-color: #2b8eca; color: white; }
button.danger { background: #67212a; border-color: #a33a45; color: #ffe9ed; }
button.ghost { background: #121927; }
button:disabled { opacity: .48; cursor: default; }
.stack { display: grid; gap: 7px; }
.row { display: flex; gap: 8px; align-items: center; min-width: 0; }
.row > * { min-width: 0; }
.full { width: 100%; }
#timeline-panel { min-height: 0; border-top: 1px solid var(--line); background: #0d1420; display: grid; grid-template-rows: 36px minmax(0, 1fr) 24px; }
#timeline-toolbar { display: grid; grid-template-columns: 240px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 6px 12px; border-bottom: 1px solid #1e2a40; box-sizing: border-box; }
#timeline-title { font-size: 12px; font-weight: 650; color: #dce7ff; }
#timeline-controls { display: flex; gap: 6px; align-items: center; justify-content: flex-end; }
#timeline-scroll { min-height: 0; overflow: auto hidden; }
#timeline { position: relative; min-width: 900px; height: 100%; background: #08101b; user-select: none; }
#frame-ruler { position: absolute; left: 120px; right: 16px; top: 0; height: 28px; border-bottom: 1px solid #23304a; }
#track-area { position: absolute; left: 0; right: 0; top: 28px; bottom: 0; }
#playhead { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--accent); z-index: 8; box-shadow: 0 0 0 1px rgba(255, 212, 95, .18); }
#playhead-label { position: absolute; top: 2px; transform: translateX(-50%); background: #231e0b; color: var(--accent); border: 1px solid rgba(255, 212, 95, .38); border-radius: 4px; padding: 1px 5px; font: 10px ui-monospace, monospace; z-index: 9; }
.track-header { position: absolute; left: 0; width: 112px; height: 24px; padding: 5px 8px 0 0; box-sizing: border-box; text-align: right; color: #aab8d6; font: 11px ui-monospace, monospace; border-right: 1px solid #23304a; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.track-line { position: absolute; left: 120px; right: 16px; height: 1px; background: rgba(64, 78, 112, .35); }
.anchorBlock { position: absolute; height: 17px; border-radius: 4px; opacity: .78; cursor: pointer; border: 1px solid rgba(255,255,255,.2); box-sizing: border-box; }
.anchorBlock:hover { opacity: 1; transform: translateY(-1px); }
.anchorBlock.selected { opacity: 1; border-color: #ffe083; box-shadow: 0 0 0 2px rgba(255, 211, 90, .26); }
.anchorBlock.edited { border-color: var(--green); }
.anchorBlock.failed { border-color: var(--red); background-image: repeating-linear-gradient(45deg, rgba(255,255,255,.18) 0 4px, transparent 4px 8px); }
.anchorBlock.clamped, .anchorBlock.suspicious { border-color: var(--orange); }
.tick { position: absolute; top: 6px; color: #7184a8; font: 10px ui-monospace, monospace; transform: translateX(-50%); }
.minorTick { position: absolute; top: 18px; width: 1px; height: 8px; background: rgba(113, 132, 168, .45); }
#statusbar { display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-top: 1px solid #1e2a40; color: #9fb0d0; font: 11px ui-monospace, monospace; overflow: hidden; }
#status-left, #status-right { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
"""


def _editor_shell_js() -> str:
    return """
const boot = BOOT_STATE;
document.getElementById('viewer').src = boot.viser_url;
let state = null;
let dragging = false;
let pendingFrame = null;
let pendingFrameTimer = null;
let lastFramePostMs = 0;
let framePostInFlight = false;
let zoom = 1.0;
const FRAME_POST_INTERVAL_MS = 50;
const timeline = document.getElementById('timeline');
const timelineScroll = document.getElementById('timeline-scroll');
const playhead = document.getElementById('playhead');
const playheadLabel = document.getElementById('playhead-label');
const recentSelect = document.getElementById('recent');
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function $(id) { return document.getElementById(id); }
function esc(value) { return String(value ?? '').replace(/[&<>\"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch])); }
function railWidth() { return Math.max(1, (timeline.clientWidth - 136) * zoom); }
function railLeft() { return 120; }
function frameToX(frame) { return railLeft() + (frame / Math.max(1, state.n_frames - 1)) * railWidth(); }
function xToFrame(clientX) {
  const rect = timeline.getBoundingClientRect();
  const ratio = clamp((clientX - rect.left - railLeft() + timelineScroll.scrollLeft) / railWidth(), 0, 1);
  return Math.round(ratio * Math.max(0, state.n_frames - 1));
}
function selectedAnchor() { return state?.selected_anchor || null; }
function statusClass(status) { return String(status || 'bound').replace(/[^a-zA-Z0-9_-]/g, '_'); }
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
    const res = await fetch('/api/frame', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({frame})});
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
  const frameText = `${state.current_frame} / ${Math.max(0, state.n_frames - 1)}`;
  $('frame-chip').textContent = `frame ${frameText}`;
  $('frame-input').value = state.current_frame;
  $('play').textContent = state.playing ? 'Pause' : 'Play';
  $('motion-title').textContent = state.motion_name || '-';
  $('pending-chip').textContent = `pending ${state.pending_edit_count || 0}`;
  $('status-left').textContent = state.last_error || state.last_message || 'Ready';
  $('status-right').textContent = `frame ${frameText} | selected ${state.selected_anchor_id || '-'} | failed ${state.binding_counts?.failed_count || 0}`;
  $('viewport-frame').textContent = frameText;
  $('viewport-selected').textContent = state.selected_anchor_id || 'no anchor';
}
function renderLeftPanel() {
  const counts = state.binding_counts || {};
  const layers = state.layers || {};
  const selectedRecent = recentSelect.value;
  recentSelect.innerHTML = '';
  (state.recent_motions || []).forEach((item, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = item.label || item.motion_path;
    recentSelect.appendChild(option);
  });
  if (selectedRecent && Number(selectedRecent) < recentSelect.options.length) recentSelect.value = selectedRecent;
  $('layer-summary').innerHTML = `
    <div class="kv">
      <div class="key">source</div><div class="value" title="${esc(layers.contact_layer)}">${esc(layers.contact_layer || '-')}</div>
      <div class="key">output</div><div class="value" title="${esc(layers.output_contact_layer)}">${esc(layers.output_contact_layer || '-')}</div>
      <div class="key">session</div><div class="value" title="${esc(layers.session_dir)}">${esc(layers.session_dir || '-')}</div>
    </div>`;
  $('binding-summary').innerHTML = `
    <span class="badge">anchors ${counts.anchor_count || 0}</span>
    <span class="badge">bound ${counts.bound_count || 0}</span>
    <span class="badge failed">failed ${counts.failed_count || 0}</span>
    <span class="badge clamped">clamped ${counts.clamped_count || 0}</span>`;
  const errors = [state.last_error, state.last_message].filter(Boolean);
  $('warning-list').innerHTML = errors.length ? errors.map(item => `<div class="${state.last_error ? 'error' : 'muted'}">${esc(item)}</div>`).join('') : '<div class="muted">No warnings.</div>';
}
function renderInspector() {
  const anchor = selectedAnchor();
  if (!anchor) {
    $('selected-anchor-card').innerHTML = '<h3>Selected Anchor</h3><div class="muted">No anchor selected.</div>';
    $('surface-card').innerHTML = '<h3>Surface Binding</h3><div class="muted">Select an anchor.</div>';
    $('edit-card').innerHTML = '<h3>Edit</h3><div class="muted">No pending edit selected.</div>';
    return;
  }
  const duration = Math.max(0, (anchor.end_frame || 0) - (anchor.start_frame || 0) + 1);
  $('selected-anchor-card').innerHTML = `<h3>Selected Anchor <span class="status-badge ${statusClass(anchor.status)}">${esc(anchor.status)}</span></h3>
    <div class="kv">
      <div class="key">id</div><div class="value" title="${esc(anchor.anchor_id)}">${esc(anchor.anchor_id)}</div>
      <div class="key">body</div><div class="value">${esc(anchor.body)}</div>
      <div class="key">frames</div><div class="value">${anchor.start_frame} -> ${anchor.end_frame}</div>
      <div class="key">duration</div><div class="value">${duration} frames</div>
    </div>`;
  const coords = anchor.surface_coordinates || {};
  $('surface-card').innerHTML = `<h3>Surface Binding</h3>
    <div class="kv">
      <div class="key">surface</div><div class="value" title="${esc(anchor.surface_id)}">${esc(anchor.surface_id || '-')}</div>
      <div class="key">object</div><div class="value" title="${esc(anchor.object_id)}">${esc(anchor.object_id || '-')}</div>
      <div class="key">type</div><div class="value">${esc(anchor.surface_type || '-')}</div>
      <div class="key">u/v</div><div class="value">${coords.u ?? '-'} / ${coords.v ?? '-'}</div>
      <div class="key">failure</div><div class="value">${esc(anchor.failure_reason || '-')}</div>
    </div>`;
  const edit = anchor.latest_edit || {};
  $('edit-card').innerHTML = `<h3>Edit</h3>
    <div class="kv">
      <div class="key">old</div><div class="value" title="${esc(JSON.stringify(edit.old_world_position || anchor.world_position || []))}">${esc(JSON.stringify(edit.old_world_position || '-'))}</div>
      <div class="key">new</div><div class="value" title="${esc(JSON.stringify(edit.new_world_position || []))}">${esc(JSON.stringify(edit.new_world_position || '-'))}</div>
      <div class="key">delta</div><div class="value">${esc(JSON.stringify(edit.delta_world || '-'))}</div>
      <div class="key">tangent</div><div class="value">${esc(JSON.stringify(edit.tangent_delta || '-'))}</div>
      <div class="key">mode</div><div class="value">${esc(edit.constraint_mode || '-')}</div>
    </div>`;
}
function renderGenerationCard() {
  const gen = state.generation || {};
  $('generation-card').innerHTML = `<h3>Generation</h3>
    <div class="stack">
      <div class="kv">
        <div class="key">solver</div><div class="value">ik_subprocess</div>
        <div class="key">mesh</div><div class="value">configured in backend</div>
        <div class="key">status</div><div class="value">${esc(gen.last_error || gen.last_output_motion || 'idle')}</div>
      </div>
      <button id="generate-disabled" class="primary" disabled title="Use the Viser-side Generate button for now.">Generate</button>
    </div>`;
}
function updatePlayhead() {
  if (!state) return;
  const x = frameToX(state.current_frame);
  playhead.style.left = x + 'px';
  playheadLabel.style.left = x + 'px';
  playheadLabel.textContent = String(state.current_frame);
}
function bodyOrder(body) {
  const order = ['right_foot', 'left_foot', 'right_hand', 'left_hand'];
  const lower = String(body || '').toLowerCase();
  const found = order.findIndex(item => lower.includes(item));
  return found >= 0 ? found : 10;
}
function renderTimeline() {
  const bodies = [...(state.bodies || [])].sort((a, b) => bodyOrder(a) - bodyOrder(b) || String(a).localeCompare(String(b)));
  const minWidth = Math.max(900, railLeft() + 16 + railWidth());
  timeline.style.width = `${minWidth}px`;
  for (const el of [...timeline.querySelectorAll('.track-header,.track-line,.anchorBlock,.tick,.minorTick')]) el.remove();
  const majorCount = 8;
  for (let i = 0; i <= majorCount; i++) {
    const frame = Math.round((Math.max(0, state.n_frames - 1) * i) / majorCount);
    const tick = document.createElement('div');
    tick.className = 'tick';
    tick.style.left = frameToX(frame) + 'px';
    tick.textContent = String(frame);
    $('frame-ruler').appendChild(tick);
  }
  const minorCount = 32;
  for (let i = 0; i <= minorCount; i++) {
    const frame = Math.round((Math.max(0, state.n_frames - 1) * i) / minorCount);
    const tick = document.createElement('div');
    tick.className = 'minorTick';
    tick.style.left = frameToX(frame) + 'px';
    $('frame-ruler').appendChild(tick);
  }
  const laneTop = 6;
  const laneH = 26;
  bodies.forEach((body, i) => {
    const y = laneTop + i * laneH;
    const header = document.createElement('div');
    header.className = 'track-header';
    header.style.top = y + 'px';
    header.textContent = body;
    $('track-area').appendChild(header);
    const line = document.createElement('div');
    line.className = 'track-line';
    line.style.top = (y + laneH - 1) + 'px';
    $('track-area').appendChild(line);
  });
  state.anchors.forEach(anchor => {
    const lane = Math.max(0, bodies.indexOf(anchor.body));
    const start = clamp(anchor.start_frame, 0, Math.max(0, state.n_frames - 1));
    const end = clamp(anchor.end_frame, start + 1, state.n_frames);
    const el = document.createElement('div');
    el.className = 'anchorBlock ' + statusClass(anchor.status) + (anchor.anchor_id === state.selected_anchor_id ? ' selected' : '');
    el.style.left = frameToX(start) + 'px';
    el.style.width = Math.max(3, frameToX(end - 1) - frameToX(start)) + 'px';
    el.style.top = (laneTop + lane * laneH + 4) + 'px';
    el.style.background = anchor.color || '#55b4ff';
    el.title = `${anchor.anchor_id}\n${anchor.body} ${anchor.start_frame}-${anchor.end_frame}\n${anchor.surface_id || ''}\n${anchor.status || ''}`;
    el.onclick = event => { event.stopPropagation(); api('/api/select_anchor', {anchor_id: anchor.anchor_id, frame: anchor.start_frame}); };
    $('track-area').appendChild(el);
  });
  updatePlayhead();
}
function render() {
  if (!state) return;
  updateChrome();
  renderLeftPanel();
  renderInspector();
  renderGenerationCard();
  renderTimeline();
}
function scrub(event, commit=false) { const frame = xToFrame(event.clientX); setLocalFrame(frame); scheduleFramePost(frame, commit); }
timeline.addEventListener('pointerdown', event => { dragging = true; timeline.setPointerCapture(event.pointerId); scrub(event); });
timeline.addEventListener('pointermove', event => { if (dragging) scrub(event); });
timeline.addEventListener('pointerup', event => { if (dragging) scrub(event, true); dragging = false; });
timeline.addEventListener('pointercancel', event => { if (dragging) scrub(event, true); dragging = false; });
timeline.addEventListener('wheel', event => { if (!event.ctrlKey && !event.metaKey) return; event.preventDefault(); zoom = clamp(zoom * (event.deltaY < 0 ? 1.18 : 0.85), 0.45, 5); renderTimeline(); }, {passive: false});
$('play').onclick = () => api('/api/play', {playing: !state.playing});
$('prev').onclick = () => api('/api/frame', {frame: state.current_frame - 1});
$('next').onclick = () => api('/api/frame', {frame: state.current_frame + 1});
$('frame-input').onchange = () => api('/api/frame', {frame: Number($('frame-input').value || 0)});
$('fit').onclick = () => { zoom = 1.0; renderTimeline(); };
$('zoom-out').onclick = () => { zoom = clamp(zoom * 0.8, 0.45, 5); renderTimeline(); };
$('zoom-in').onclick = () => { zoom = clamp(zoom * 1.25, 0.45, 5); renderTimeline(); };
$('snap-selected').onclick = () => { const a = selectedAnchor(); if (a) api('/api/frame', {frame: a.start_frame}); };
$('prev-anchor').onclick = () => selectRelativeAnchor(-1);
$('next-anchor').onclick = () => selectRelativeAnchor(1);
recentSelect.onchange = () => api('/api/open_recent', {index: Number(recentSelect.value || 0)});
$('load-motion').onclick = () => api('/api/load_motion', {});
$('discard').onclick = () => api('/api/discard', {});
function selectRelativeAnchor(offset) {
  if (!state?.anchors?.length) return;
  const ids = state.anchors.map(a => a.anchor_id);
  const current = Math.max(0, ids.indexOf(state.selected_anchor_id));
  const next = state.anchors[(current + offset + state.anchors.length) % state.anchors.length];
  api('/api/select_anchor', {anchor_id: next.anchor_id, frame: next.start_frame});
}
window.addEventListener('keydown', event => {
  if (!state) return;
  if (event.code === 'Space') { event.preventDefault(); api('/api/play', {playing: !state.playing}); }
  if (event.code === 'ArrowLeft') api('/api/frame', {frame: state.current_frame - (event.shiftKey ? 10 : 1)});
  if (event.code === 'ArrowRight') api('/api/frame', {frame: state.current_frame + (event.shiftKey ? 10 : 1)});
});
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
    <div id="transport">
      <button id="prev" class="ghost">Prev</button>
      <button id="play" class="primary">Play</button>
      <button id="next" class="ghost">Next</button>
      <input id="frame-input" type="number" min="0" value="0" />
      <span id="frame-chip">frame -</span>
    </div>
    <div id="app-actions">
      <span id="pending-chip">pending 0</span>
      <button id="discard" class="danger">Discard</button>
      <button id="generate-top" class="primary" disabled title="Generation is shown in the inspector; current backend button remains in Viser fallback.">Generate</button>
    </div>
  </header>
  <main id="main">
    <aside id="left-panel">
      <section class="card"><h3>Motion</h3><div class="stack"><select id="recent" class="full"></select><button id="load-motion" class="primary">Load Motion...</button><div class="muted">Opens the local motion file picker.</div></div></section>
      <section class="card"><h3>Layers</h3><div id="layer-summary"></div></section>
      <section class="card"><h3>Filters</h3><div class="stack"><button class="ghost" disabled>Body/status filters in next pass</button><div id="binding-summary" class="row"></div></div></section>
      <section class="card"><h3>Warnings</h3><div id="warning-list"></div></section>
    </aside>
    <section id="viewer-panel">
      <iframe id="viewer"></iframe>
      <div class="viewport-hud"><span id="viewport-frame" class="badge">-</span><span id="viewport-selected" class="badge">no anchor</span></div>
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
      <div id="timeline-title">Contact Sequencer</div>
      <div class="muted">Click blocks to select. Drag empty timeline to scrub.</div>
      <div id="timeline-controls">
        <button id="fit" class="ghost">Fit</button>
        <button id="zoom-out" class="ghost">-</button>
        <button id="zoom-in" class="ghost">+</button>
        <button id="snap-selected" class="ghost">Snap selected</button>
        <button id="prev-anchor" class="ghost">Prev anchor</button>
        <button id="next-anchor" class="ghost">Next anchor</button>
      </div>
    </div>
    <div id="timeline-scroll"><div id="timeline"><div id="frame-ruler"></div><div id="track-area"></div><div id="playhead"></div><div id="playhead-label"></div></div></div>
    <div id="statusbar"><div id="status-left">Ready</div><div id="status-right"></div></div>
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
                elif path == "/api/discard":
                    controller.discard()
                elif path == "/api/open_recent":
                    controller.open_recent_motion(int(body.get("index", 0)))
                elif path == "/api/load_motion":
                    if hasattr(controller, "open_load_dialog"):
                        controller.open_load_dialog()
                    else:
                        controller.state.last_error = "load dialog is unavailable in this editor mode"
                elif path == "/api/open_latest":
                    controller.open_latest_motion()
                elif path == "/api/reload_motion":
                    controller.reload_current_motion()
                else:
                    controller.state.last_error = f"unknown timeline API path: {path}"
            except Exception as exc:
                controller.state.last_error = str(exc)
            self._send_json(state())

        def log_message(self, _format: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", int(timeline_port)), TimelineHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
