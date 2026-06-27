from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from motion_edit.segmentation.session import (
    SegmentationEditSession,
    add_draft_segment,
    delete_draft_segment,
    discard_segmentation_edit_session,
    list_draft_segments,
    read_draft_segments,
    relabel_draft_segment,
    save_segmentation_edit_session,
    trim_draft_segment,
)


@dataclass
class SegmentationTimelineController:
    session: SegmentationEditSession
    current_frame: int = 0
    selected_segment_id: str | None = None
    editing_segment_id: str | None = None
    preview_start_frame: int | None = None
    preview_end_frame: int | None = None
    last_message: str | None = "Ready"
    last_error: str | None = None

    def segments(self):
        return list_draft_segments(self.session)

    @property
    def n_frames(self) -> int:
        return max((segment.end_frame for segment in self.segments()), default=1)

    def select_segment(self, segment_id: str, *, frame: int | None = None) -> None:
        segment = self._segment(segment_id)
        self.selected_segment_id = segment.segment_id
        self.editing_segment_id = None
        self.preview_start_frame = None
        self.preview_end_frame = None
        self.current_frame = int(frame if frame is not None else segment.start_frame)
        self.last_error = None
        self.last_message = f"selected {segment.segment_id}"

    def begin_boundary_edit(self) -> None:
        if not self.selected_segment_id:
            raise ValueError("select a segment before editing")
        segment = self._segment(self.selected_segment_id)
        self.editing_segment_id = segment.segment_id
        self.preview_start_frame = segment.start_frame
        self.preview_end_frame = segment.end_frame
        self.last_error = None
        self.last_message = f"editing boundary for {segment.segment_id}"

    def preview_boundary(self, *, start_frame: int, end_frame: int) -> None:
        if not self.editing_segment_id:
            raise ValueError("enter boundary edit mode before previewing")
        if int(end_frame) <= int(start_frame):
            raise ValueError("end_frame must be greater than start_frame")
        self.preview_start_frame = int(start_frame)
        self.preview_end_frame = int(end_frame)
        self.last_error = None
        self.last_message = f"preview {self.editing_segment_id}: {start_frame}->{end_frame}"

    def apply_boundary(self, *, reason: str | None = None, allow_overlap: bool = False) -> None:
        if not self.editing_segment_id:
            raise ValueError("enter boundary edit mode before applying")
        if self.preview_start_frame is None or self.preview_end_frame is None:
            raise ValueError("no boundary preview is active")
        segment = trim_draft_segment(
            self.session,
            segment_id=self.editing_segment_id,
            start_frame=self.preview_start_frame,
            end_frame=self.preview_end_frame,
            reason=reason or "timeline boundary edit",
            allow_overlap=allow_overlap,
        )
        self.selected_segment_id = segment.segment_id
        self.current_frame = segment.start_frame
        self.editing_segment_id = None
        self.preview_start_frame = None
        self.preview_end_frame = None
        self.last_error = None
        self.last_message = f"applied boundary edit to {segment.segment_id}"

    def cancel_boundary(self) -> None:
        self.editing_segment_id = None
        self.preview_start_frame = None
        self.preview_end_frame = None
        self.last_error = None
        self.last_message = "cancelled boundary edit"

    def add_segment(self, *, start_frame: int, end_frame: int) -> None:
        segment = add_draft_segment(
            self.session,
            start_frame=int(start_frame),
            end_frame=int(end_frame),
            reason="timeline add segment",
            allow_overlap=True,
        )
        self.selected_segment_id = segment.segment_id
        self.current_frame = segment.start_frame
        self.last_error = None
        self.last_message = f"added {segment.segment_id}"

    def delete_selected(self) -> None:
        if not self.selected_segment_id:
            raise ValueError("select a segment before deleting")
        deleted = delete_draft_segment(self.session, segment_id=self.selected_segment_id, reason="timeline delete segment")
        self.selected_segment_id = None
        self.editing_segment_id = None
        self.preview_start_frame = None
        self.preview_end_frame = None
        self.current_frame = deleted.start_frame
        self.last_error = None
        self.last_message = f"deleted {deleted.segment_id}"

    def relabel_selected(
        self,
        *,
        active_body: str | None = None,
        support_bodies: list[str] | None = None,
        transition_type: str | None = None,
        status: str | None = None,
    ) -> None:
        if not self.selected_segment_id:
            raise ValueError("select a segment before relabeling")
        segment = relabel_draft_segment(
            self.session,
            segment_id=self.selected_segment_id,
            active_body=active_body or None,
            support_bodies=support_bodies or [],
            transition_type=transition_type or None,
            status=status or None,
            reason="timeline relabel segment",
        )
        self.selected_segment_id = segment.segment_id
        self.last_error = None
        self.last_message = f"relabeled {segment.segment_id}"

    def save(self, *, reason: str | None = None, allow_overlap: bool = False) -> None:
        out = save_segmentation_edit_session(self.session, reason=reason or "timeline save segmentation", allow_overlap=allow_overlap)
        self.last_error = None
        self.last_message = f"saved canonical segmentation {out}"

    def discard(self) -> None:
        discard_segmentation_edit_session(self.session, reason="timeline discard segmentation")
        self.last_error = None
        self.last_message = f"discarded {self.session.session_id}"

    def state(self) -> dict[str, Any]:
        segments = []
        selected = None
        for index, segment in enumerate(self.segments()):
            metadata = segment.metadata or {}
            item = {
                "index": index,
                "segment_id": segment.segment_id,
                "motion_id": segment.motion_id,
                "start_frame": int(segment.start_frame),
                "end_frame": int(segment.end_frame),
                "status": segment.status,
                "source": segment.source,
                "active": segment.active,
                "support": segment.support,
                "active_body": metadata.get("active_body") or segment.active,
                "support_bodies": metadata.get("support_bodies") or ([] if segment.support is None else [segment.support]),
                "transition_type": metadata.get("transition_type") or "",
                "is_selected": segment.segment_id == self.selected_segment_id,
                "is_editing": segment.segment_id == self.editing_segment_id,
            }
            if item["is_editing"]:
                item["preview_start_frame"] = self.preview_start_frame
                item["preview_end_frame"] = self.preview_end_frame
            segments.append(item)
            if item["is_selected"]:
                selected = item
        return {
            "schema_version": 1,
            "session_id": self.session.session_id,
            "motion_version_id": self.session.motion_version_id,
            "motion_name": Path(self.session.motion_path).name,
            "n_frames": max(1, self.n_frames),
            "current_frame": max(0, min(self.current_frame, max(0, self.n_frames - 1))),
            "selected_segment_id": self.selected_segment_id,
            "editing_segment_id": self.editing_segment_id,
            "segments": segments,
            "selected_segment": selected,
            "last_message": self.last_message,
            "last_error": self.last_error,
        }

    def _segment(self, segment_id: str):
        for segment in read_draft_segments(self.session):
            if segment.segment_id == segment_id:
                return segment
        raise ValueError(f"segment not found: {segment_id}")


def _css() -> str:
    return """
:root { color-scheme: dark; --bg:#070a10; --panel:#101723; --line:#27344d; --muted:#8fa1c3; --text:#e7edf9; --accent:#ffd45f; --green:#7ee08c; --red:#ff6b72; --orange:#ffad5c; }
html, body { margin:0; height:100%; background:var(--bg); color:var(--text); font-family:Inter,system-ui,sans-serif; overflow:hidden; }
#app { height:100%; display:grid; grid-template-rows:42px minmax(0,1fr) 270px; }
#appbar { display:grid; grid-template-columns:340px minmax(0,1fr) 520px; gap:12px; align-items:center; padding:0 12px; border-bottom:1px solid var(--line); background:#0d1420; box-sizing:border-box; }
#brand { display:flex; gap:10px; align-items:baseline; min-width:0; }
#title { font-size:15px; font-weight:700; white-space:nowrap; }
#motion-title { color:var(--muted); font:12px ui-monospace,monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
#transport, #actions { display:flex; gap:8px; align-items:center; justify-content:center; min-width:0; }
#actions { justify-content:flex-end; }
button, input, select { height:28px; border:1px solid #34415f; border-radius:5px; background:#111a29; color:#dce7ff; padding:0 8px; box-sizing:border-box; }
button { cursor:pointer; } button.primary { background:#1d5f8f; border-color:#2b8eca; color:#fff; } button.danger { background:#67212a; border-color:#a33a45; color:#ffe9ed; } button.ghost { background:#121927; } button:disabled { opacity:.48; cursor:default; }
.badge { border:1px solid var(--line); border-radius:999px; background:#121b2a; color:#cdd9f0; padding:4px 8px; font:12px ui-monospace,monospace; }
#main { min-height:0; display:grid; grid-template-columns:minmax(0,1fr) 340px; background:#05070c; }
#viewer { width:100%; height:100%; border:0; background:#05070c; }
#inspector { min-width:0; overflow:auto; background:var(--panel); border-left:1px solid var(--line); padding:10px; box-sizing:border-box; }
.card { border:1px solid var(--line); border-radius:7px; background:#0b111b; padding:10px; margin-bottom:10px; }
.card h3 { margin:0 0 8px; font-size:12px; color:#dbe6fa; display:flex; justify-content:space-between; gap:8px; }
.kv { display:grid; grid-template-columns:92px minmax(0,1fr); gap:6px 8px; font-size:12px; color:#c5d1e8; }
.kv .key { color:var(--muted); } .kv .value { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-family:ui-monospace,monospace; }
.stack { display:grid; gap:7px; } .row { display:flex; gap:8px; align-items:center; min-width:0; } .row > * { min-width:0; } .full { width:100%; }
.muted { color:var(--muted); } .error { color:var(--red); } .warn { color:var(--orange); }
#timeline-panel { min-height:0; border-top:1px solid var(--line); background:#0d1420; display:grid; grid-template-rows:34px minmax(0,1fr) 24px; }
#timeline-toolbar { display:grid; grid-template-columns:220px minmax(0,1fr) auto; gap:10px; align-items:center; padding:5px 12px; border-bottom:1px solid #1e2a40; box-sizing:border-box; }
#timeline-title { font-size:12px; font-weight:650; color:#dce7ff; }
#timeline-controls { display:flex; gap:6px; align-items:center; justify-content:flex-end; }
#timeline-scroll { min-height:0; overflow:auto hidden; }
#timeline { position:relative; min-width:900px; height:100%; background:#08101b; user-select:none; }
#frame-ruler { position:absolute; left:120px; right:16px; top:0; height:28px; border-bottom:1px solid #23304a; }
#track-area { position:absolute; left:0; right:0; top:28px; bottom:0; }
#playhead { position:absolute; top:0; bottom:0; width:2px; background:var(--accent); z-index:8; }
#playhead-label { position:absolute; top:2px; transform:translateX(-50%); background:#231e0b; color:var(--accent); border:1px solid rgba(255,212,95,.38); border-radius:4px; padding:1px 5px; font:10px ui-monospace,monospace; z-index:9; }
.track-header { position:absolute; left:0; width:112px; height:24px; padding:5px 8px 0 0; box-sizing:border-box; text-align:right; color:#aab8d6; font:11px ui-monospace,monospace; border-right:1px solid #23304a; background:#08101b; }
.track-line { position:absolute; left:120px; right:16px; height:1px; background:rgba(64,78,112,.35); }
.segBlock { position:absolute; height:28px; border-radius:5px; opacity:.78; cursor:pointer; border:1px solid rgba(255,255,255,.2); box-sizing:border-box; background:#2c6f99; }
.segBlock:hover { opacity:1; transform:translateY(-1px); }
.segBlock.selected { opacity:1; border-color:#ffe083; box-shadow:0 0 0 2px rgba(255,211,90,.42); z-index:6; }
.segBlock.editing { border-color:var(--green); box-shadow:0 0 0 2px rgba(126,224,140,.35); }
.segBlock.accepted { background:#277b55; } .segBlock.rejected { background:#65313b; } .segBlock.manual { background:#7b6431; }
.segLabel { position:absolute; left:7px; right:7px; top:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font:11px ui-monospace,monospace; color:#edf5ff; pointer-events:none; }
.segHandle { position:absolute; top:-5px; bottom:-5px; width:8px; background:var(--accent); border:1px solid #fff1a6; border-radius:3px; z-index:10; cursor:ew-resize; }
.segHandle.left { left:-5px; } .segHandle.right { right:-5px; }
.tick { position:absolute; top:6px; color:#7184a8; font:10px ui-monospace,monospace; transform:translateX(-50%); }
.minorTick { position:absolute; top:18px; width:1px; height:8px; background:rgba(113,132,168,.45); }
#status-bar { display:flex; align-items:center; justify-content:space-between; padding:0 12px; border-top:1px solid #1e2a40; color:#9fb0d0; font:11px ui-monospace,monospace; overflow:hidden; }
#status-left, #status-right { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; user-select:text; }
"""


def _js() -> str:
    return """
const boot = BOOT_STATE;
document.getElementById('viewer').src = boot.viser_url;
let state = null;
let draggingFrame = false;
let draggingHandle = null;
let localPreview = null;
const timeline = document.getElementById('timeline');
const timelineScroll = document.getElementById('timeline-scroll');
const playhead = document.getElementById('playhead');
const playheadLabel = document.getElementById('playhead-label');
function $(id) { return document.getElementById(id); }
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function esc(value) { return String(value ?? '').replace(/[&<>\"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[ch])); }
function railWidth() { return Math.max(1, timeline.clientWidth - 136); }
function railLeft() { return 120; }
function frameToX(frame) { return railLeft() + (frame / Math.max(1, state.n_frames - 1)) * railWidth(); }
function xToFrame(clientX) { const rect = timeline.getBoundingClientRect(); const ratio = clamp((clientX - rect.left - railLeft() + timelineScroll.scrollLeft) / railWidth(), 0, 1); return Math.round(ratio * Math.max(0, state.n_frames - 1)); }
function selectedSegment() { return state?.selected_segment || null; }
async function api(path, body) { const res = await fetch(path, {method: body ? 'POST' : 'GET', headers: {'Content-Type':'application/json'}, body: body ? JSON.stringify(body) : undefined}); state = await res.json(); localPreview = null; render(); return state; }
async function refresh() { if (!draggingFrame && !draggingHandle) await api('/api/state'); }
function updateChrome() { if (!state) return; const frameText = `${state.current_frame} / ${Math.max(0, state.n_frames - 1)}`; $('motion-title').textContent = `${state.motion_name || '-'} | ${state.session_id}`; $('frame-chip').textContent = `frame ${frameText}`; $('frame-input').value = state.current_frame; $('status-left').textContent = state.last_error ? `Error: ${state.last_error}` : (state.last_message || 'Ready'); $('status-right').textContent = `selected ${state.selected_segment_id || '-'} | editing ${state.editing_segment_id || '-'} | segments ${(state.segments || []).length}`; }
function updatePlayhead() { const x = frameToX(state.current_frame); playhead.style.left = x + 'px'; playheadLabel.style.left = x + 'px'; playheadLabel.textContent = String(state.current_frame); }
function renderInspector() { const seg = selectedSegment(); if (!seg) { $('selected-card').innerHTML = '<h3>Selected Segment</h3><div class="muted">No segment selected.</div>'; $('edit-card').innerHTML = '<h3>Boundary Edit</h3><div class="muted">Select a segment.</div>'; return; } const start = localPreview?.start_frame ?? seg.preview_start_frame ?? seg.start_frame; const end = localPreview?.end_frame ?? seg.preview_end_frame ?? seg.end_frame; $('selected-card').innerHTML = `<h3>Selected Segment <span class="badge">${esc(seg.status)}</span></h3><div class="kv"><div class="key">id</div><div class="value" title="${esc(seg.segment_id)}">${esc(seg.segment_id)}</div><div class="key">frames</div><div class="value">${seg.start_frame} -> ${seg.end_frame}</div><div class="key">active</div><div class="value">${esc(seg.active_body || '-')}</div><div class="key">support</div><div class="value">${esc(JSON.stringify(seg.support_bodies || []))}</div><div class="key">transition</div><div class="value">${esc(seg.transition_type || '-')}</div></div>`; $('edit-card').innerHTML = `<h3>Boundary Edit</h3><div class="stack"><div class="kv"><div class="key">mode</div><div class="value">${seg.is_editing ? 'editing selected segment' : 'view only'}</div><div class="key">preview</div><div class="value">${start} -> ${end}</div></div><div class="row"><button id="edit-selected" class="primary">Edit selected</button><button id="apply-boundary" class="primary" ${seg.is_editing ? '' : 'disabled'}>Apply boundary</button><button id="cancel-boundary" class="ghost" ${seg.is_editing ? '' : 'disabled'}>Cancel</button></div><div class="row"><input id="active-body" placeholder="active_body" value="${esc(seg.active_body || '')}"><input id="transition-type" placeholder="transition_type" value="${esc(seg.transition_type || '')}"></div><div class="row"><input id="support-bodies" placeholder="support bodies comma separated" value="${esc((seg.support_bodies || []).join(','))}"><select id="seg-status"><option>candidate</option><option>manual</option><option>accepted</option><option>rejected</option></select></div><div class="row"><button id="relabel-seg" class="ghost">Relabel</button><button id="delete-seg" class="danger">Delete selected</button></div></div>`; $('seg-status').value = seg.status || 'candidate'; $('edit-selected').onclick = () => api('/api/begin_boundary_edit', {}); $('apply-boundary').onclick = () => api('/api/apply_boundary', {start_frame: start, end_frame: end}); $('cancel-boundary').onclick = () => api('/api/cancel_boundary', {}); $('delete-seg').onclick = () => { if (confirm('Delete selected segment from draft?')) api('/api/delete_segment', {}); }; $('relabel-seg').onclick = () => api('/api/relabel_segment', {active_body: $('active-body').value, support_bodies: $('support-bodies').value.split(',').map(x => x.trim()).filter(Boolean), transition_type: $('transition-type').value, status: $('seg-status').value}); }
function renderTimeline() { timeline.style.width = Math.max(900, timelineScroll.clientWidth) + 'px'; for (const el of [...timeline.querySelectorAll('.track-header,.track-line,.segBlock,.tick,.minorTick')]) el.remove(); for (let i = 0; i <= 8; i++) { const frame = Math.round((Math.max(0, state.n_frames - 1) * i) / 8); const tick = document.createElement('div'); tick.className = 'tick'; tick.style.left = frameToX(frame) + 'px'; tick.textContent = String(frame); $('frame-ruler').appendChild(tick); } for (let i = 0; i <= 32; i++) { const frame = Math.round((Math.max(0, state.n_frames - 1) * i) / 32); const tick = document.createElement('div'); tick.className = 'minorTick'; tick.style.left = frameToX(frame) + 'px'; $('frame-ruler').appendChild(tick); } const header = document.createElement('div'); header.className = 'track-header'; header.style.top = '18px'; header.textContent = 'Segments'; $('track-area').appendChild(header); const line = document.createElement('div'); line.className = 'track-line'; line.style.top = '56px'; $('track-area').appendChild(line); (state.segments || []).forEach(seg => { const start = localPreview && seg.segment_id === state.editing_segment_id ? localPreview.start_frame : (seg.preview_start_frame ?? seg.start_frame); const end = localPreview && seg.segment_id === state.editing_segment_id ? localPreview.end_frame : (seg.preview_end_frame ?? seg.end_frame); const el = document.createElement('div'); el.className = `segBlock ${seg.status || ''}${seg.is_selected ? ' selected' : ''}${seg.is_editing ? ' editing' : ''}`; el.style.left = frameToX(start) + 'px'; el.style.width = Math.max(4, frameToX(Math.max(start + 1, end)) - frameToX(start)) + 'px'; el.style.top = '22px'; el.title = `${seg.segment_id}\n${start}-${end}\n${seg.status}`; el.onclick = event => { event.stopPropagation(); api('/api/select_segment', {segment_id: seg.segment_id, frame: seg.start_frame}); }; const label = document.createElement('div'); label.className = 'segLabel'; label.textContent = `${seg.index}: ${seg.segment_id}`; el.appendChild(label); if (seg.is_editing) { const left = document.createElement('div'); left.className = 'segHandle left'; left.onpointerdown = event => { event.stopPropagation(); draggingHandle = {side:'left', segment:seg}; timeline.setPointerCapture(event.pointerId); }; const right = document.createElement('div'); right.className = 'segHandle right'; right.onpointerdown = event => { event.stopPropagation(); draggingHandle = {side:'right', segment:seg}; timeline.setPointerCapture(event.pointerId); }; el.appendChild(left); el.appendChild(right); } $('track-area').appendChild(el); }); updatePlayhead(); }
function render() { if (!state) return; updateChrome(); renderInspector(); renderTimeline(); }
function setFrame(frame) { state.current_frame = clamp(frame, 0, Math.max(0, state.n_frames - 1)); updateChrome(); updatePlayhead(); }
timeline.addEventListener('pointerdown', event => { if (event.target.classList.contains('segHandle') || event.target.closest('.segBlock')) return; draggingFrame = true; timeline.setPointerCapture(event.pointerId); setFrame(xToFrame(event.clientX)); });
timeline.addEventListener('pointermove', event => { if (draggingHandle) { const frame = xToFrame(event.clientX); const seg = draggingHandle.segment; let start = localPreview?.start_frame ?? seg.preview_start_frame ?? seg.start_frame; let end = localPreview?.end_frame ?? seg.preview_end_frame ?? seg.end_frame; if (draggingHandle.side === 'left') start = clamp(frame, 0, end - 1); else end = clamp(frame, start + 1, state.n_frames); localPreview = {start_frame:start, end_frame:end}; render(); return; } if (draggingFrame) setFrame(xToFrame(event.clientX)); });
timeline.addEventListener('pointerup', event => { if (draggingHandle) { draggingHandle = null; return; } if (draggingFrame) { draggingFrame = false; api('/api/frame', {frame: state.current_frame}); } });
timeline.addEventListener('pointercancel', () => { draggingHandle = null; draggingFrame = false; });
$('prev').onclick = () => api('/api/frame', {frame: state.current_frame - 1});
$('next').onclick = () => api('/api/frame', {frame: state.current_frame + 1});
$('frame-input').onchange = () => api('/api/frame', {frame: Number($('frame-input').value || 0)});
$('add-seg').onclick = () => { const start = state.current_frame; api('/api/add_segment', {start_frame: start, end_frame: Math.min(state.n_frames, start + 20)}); };
$('save').onclick = () => { if (confirm('Save draft to canonical segmentation?')) api('/api/save', {}); };
$('discard').onclick = () => { if (confirm('Discard draft session?')) api('/api/discard', {}); };
window.addEventListener('keydown', event => { if (!state) return; if (event.code === 'ArrowLeft') api('/api/frame', {frame: state.current_frame - (event.shiftKey ? 10 : 1)}); if (event.code === 'ArrowRight') api('/api/frame', {frame: state.current_frame + (event.shiftKey ? 10 : 1)}); });
refresh();
setInterval(refresh, 700);
"""


def _html(*, viser_url: str) -> str:
    state_json = json.dumps({"viser_url": viser_url})
    script = _js().replace("BOOT_STATE", state_json)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Motion Edit Segmentation Timeline</title><style>{_css()}</style></head>
<body><div id="app">
<header id="appbar"><div id="brand"><div id="title">Motion Edit Segmentation</div><div id="motion-title"></div></div><div id="transport"><button id="prev" class="ghost">Prev</button><button id="next" class="ghost">Next</button><input id="frame-input" type="number" min="0" value="0"><span id="frame-chip" class="badge">frame -</span></div><div id="actions"><button id="add-seg" class="ghost">Add segment at frame</button><button id="discard" class="danger">Discard</button><button id="save" class="primary">Save segmentation</button></div></header>
<main id="main"><section><iframe id="viewer"></iframe></section><aside id="inspector"><section id="selected-card" class="card"></section><section id="edit-card" class="card"></section></aside></main>
<section id="timeline-panel"><div id="timeline-toolbar"><div id="timeline-title">Segment Timeline</div><div class="muted">Click a segment to select. Click Edit selected to show handles. Drag handles for preview; Apply writes draft.</div><div id="timeline-controls"></div></div><div id="timeline-scroll"><div id="timeline"><div id="frame-ruler"></div><div id="track-area"></div><div id="playhead"></div><div id="playhead-label"></div></div></div><div id="status-bar"><div id="status-left">Ready</div><div id="status-right"></div></div></section>
</div><script>{script}</script></body></html>"""


def start_segmentation_timeline_wrapper(
    *,
    controller: SegmentationTimelineController,
    timeline_port: int,
    viser_port: int,
) -> ThreadingHTTPServer:
    viser_url = f"http://localhost:{viser_port}"

    class Handler(BaseHTTPRequestHandler):
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
                self._send_json(controller.state())
                return
            html = _html(viser_url=viser_url).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def do_POST(self) -> None:  # noqa: N802
            body = self._read_json()
            path = urlparse(self.path).path
            try:
                if path == "/api/frame":
                    controller.current_frame = int(body.get("frame", controller.current_frame))
                elif path == "/api/select_segment":
                    controller.select_segment(str(body.get("segment_id") or ""), frame=body.get("frame"))
                elif path == "/api/begin_boundary_edit":
                    controller.begin_boundary_edit()
                elif path == "/api/preview_boundary":
                    controller.preview_boundary(start_frame=int(body["start_frame"]), end_frame=int(body["end_frame"]))
                elif path == "/api/apply_boundary":
                    controller.preview_boundary(start_frame=int(body["start_frame"]), end_frame=int(body["end_frame"]))
                    controller.apply_boundary()
                elif path == "/api/cancel_boundary":
                    controller.cancel_boundary()
                elif path == "/api/add_segment":
                    controller.add_segment(start_frame=int(body["start_frame"]), end_frame=int(body["end_frame"]))
                elif path == "/api/delete_segment":
                    controller.delete_selected()
                elif path == "/api/relabel_segment":
                    controller.relabel_selected(
                        active_body=body.get("active_body"),
                        support_bodies=list(body.get("support_bodies") or []),
                        transition_type=body.get("transition_type"),
                        status=body.get("status"),
                    )
                elif path == "/api/save":
                    controller.save()
                elif path == "/api/discard":
                    controller.discard()
                else:
                    controller.last_error = f"unknown segmentation API path: {path}"
            except Exception as exc:
                controller.last_error = str(exc)
            self._send_json(controller.state())

        def log_message(self, _format: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", int(timeline_port)), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
