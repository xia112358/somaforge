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
    for anchor in graph.anchors:
        if anchor.body not in bodies:
            bodies.append(anchor.body)
        status = "selected" if anchor.anchor_id == controller.selected_anchor_id else "bound"
        obj = controller._anchor_obj(anchor.anchor_id)
        if obj is not None:
            status = str(obj.get("status") or status)
            if anchor.anchor_id == controller.selected_anchor_id:
                status = "selected"
        anchors.append(
            {
                "anchor_id": anchor.anchor_id,
                "body": anchor.body,
                "start_frame": anchor.start_frame,
                "end_frame": anchor.end_frame,
                "surface_id": anchor.surface_id,
                "object_id": anchor.object_id,
                "status": status,
                "color": _body_color_hex(anchor.body),
            }
        )
    return {
        "schema_version": 1,
        "motion_name": motion_name,
        "n_frames": n_frames,
        "fps": int(fps),
        "current_frame": current_frame,
        "playing": bool(playback.playing["value"]) if playback is not None else False,
        "selected_anchor_id": controller.selected_anchor_id,
        "pending_edit_count": len(controller.pending_edits()),
        "last_message": controller.state.last_message,
        "last_error": controller.state.last_error,
        "bodies": bodies,
        "anchors": anchors,
    }


def _timeline_html(*, viser_url: str) -> str:
    state_json = json.dumps({"viser_url": viser_url})
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Motion Edit Contact Timeline</title>
<style>
html, body {{ margin: 0; height: 100%; background: #080b12; color: #e8ecf7; font-family: Inter, system-ui, sans-serif; overflow: hidden; }}
#app {{ height: 100%; display: grid; grid-template-rows: minmax(0, 1fr) 282px; }}
#viewer {{ width: 100%; height: 100%; border: 0; background: #05070c; }}
#panel {{ border-top: 1px solid #26314a; background: #101622; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; gap: 10px; padding: 10px 12px; box-sizing: border-box; }}
#top {{ display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center; }}
#title {{ font-size: 14px; font-weight: 650; }}
#readout, #status, #hint {{ color: #95a6c8; font: 12px ui-monospace, monospace; overflow-wrap: anywhere; }}
#controls {{ display: flex; gap: 8px; align-items: center; justify-content: flex-end; }}
button {{ height: 30px; border: 1px solid #34415f; border-radius: 5px; background: #172033; color: #dce7ff; padding: 0 10px; cursor: pointer; }}
button.primary {{ background: #1d5f8f; border-color: #2b8eca; color: white; }}
button.danger {{ background: #67212a; border-color: #a33a45; }}
#timeline {{ position: relative; min-height: 170px; border: 1px solid #28334c; border-radius: 6px; background: #0b101a; overflow: hidden; user-select: none; }}
#rail {{ position: absolute; left: 56px; right: 12px; top: 22px; height: 2px; background: #44506c; }}
#current {{ position: absolute; top: 8px; bottom: 6px; width: 2px; background: #ffd35a; z-index: 4; }}
.laneLabel {{ position: absolute; left: 8px; width: 42px; height: 18px; color: #9eb3d7; font: 11px ui-monospace, monospace; text-align: right; overflow: hidden; }}
.anchorBlock {{ position: absolute; height: 16px; border-radius: 4px; opacity: .72; cursor: pointer; border: 1px solid rgba(255,255,255,.18); box-sizing: border-box; }}
.anchorBlock:hover {{ opacity: 1; transform: translateY(-1px); }}
.anchorBlock.selected {{ opacity: 1; border-color: #ffe083; box-shadow: 0 0 0 2px rgba(255, 211, 90, .28); }}
.anchorBlock.edited {{ border-color: #82eb91; }}
.tick {{ position: absolute; top: 4px; color: #7284a8; font: 10px ui-monospace, monospace; transform: translateX(-50%); }}
#bottom {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
#message {{ color: #95a6c8; font: 12px ui-monospace, monospace; }}
</style>
</head>
<body>
<div id="app">
  <iframe id="viewer"></iframe>
  <div id="panel">
    <div id="top">
      <div id="title">Motion Edit Contact Timeline</div>
      <div id="readout"></div>
      <div id="controls">
        <button id="play" class="primary">Play</button>
        <button id="prev">Prev</button>
        <button id="next">Next</button>
        <button id="save" class="primary">Save edits</button>
        <button id="discard" class="danger">Discard</button>
      </div>
    </div>
    <div id="timeline"><div id="rail"></div><div id="current"></div></div>
    <div id="bottom"><div id="hint">Drag/click timeline to scrub. Click contact blocks to select anchors. Space=play, Arrow=step.</div><div id="message"></div></div>
  </div>
</div>
<script>
const boot = {state_json};
document.getElementById('viewer').src = boot.viser_url;
let state = null;
let dragging = false;
const timeline = document.getElementById('timeline');
const current = document.getElementById('current');
const readout = document.getElementById('readout');
const message = document.getElementById('message');
function clamp(x, lo, hi) {{ return Math.max(lo, Math.min(hi, x)); }}
function railRect() {{
  const rect = timeline.getBoundingClientRect();
  return {{left: rect.left + 56, width: Math.max(1, rect.width - 68)}};
}}
function frameToX(frame) {{
  const rr = railRect();
  return 56 + (frame / Math.max(1, state.n_frames - 1)) * rr.width;
}}
function xToFrame(clientX) {{
  const rr = railRect();
  const ratio = clamp((clientX - rr.left) / rr.width, 0, 1);
  return Math.round(ratio * Math.max(0, state.n_frames - 1));
}}
async function api(path, body) {{
  const res = await fetch(path, {{method: body ? 'POST' : 'GET', headers: {{'Content-Type': 'application/json'}}, body: body ? JSON.stringify(body) : undefined}});
  state = await res.json();
  render();
  return state;
}}
async function refresh() {{ await api('/api/state'); }}
function render() {{
  if (!state) return;
  current.style.left = frameToX(state.current_frame) + 'px';
  document.getElementById('play').textContent = state.playing ? 'Pause' : 'Play';
  readout.textContent = `${{state.motion_name}}  frame=${{state.current_frame}}/${{Math.max(0, state.n_frames - 1)}}  anchors=${{state.anchors.length}}  pending=${{state.pending_edit_count}}  selected=${{state.selected_anchor_id || '-'}}`;
  message.textContent = state.last_error || state.last_message || '';
  for (const el of [...timeline.querySelectorAll('.laneLabel,.anchorBlock,.tick')]) el.remove();
  for (const f of [0, Math.max(0, state.n_frames - 1)]) {{
    const t = document.createElement('div');
    t.className = 'tick';
    t.style.left = frameToX(f) + 'px';
    t.textContent = String(f);
    timeline.appendChild(t);
  }}
  const laneTop = 42;
  const laneH = 22;
  state.bodies.forEach((body, i) => {{
    const label = document.createElement('div');
    label.className = 'laneLabel';
    label.style.top = (laneTop + i * laneH) + 'px';
    label.textContent = body;
    timeline.appendChild(label);
  }});
  state.anchors.forEach(anchor => {{
    const lane = Math.max(0, state.bodies.indexOf(anchor.body));
    const start = clamp(anchor.start_frame, 0, Math.max(0, state.n_frames - 1));
    const end = clamp(anchor.end_frame, start + 1, state.n_frames);
    const el = document.createElement('div');
    el.className = 'anchorBlock' + (anchor.anchor_id === state.selected_anchor_id ? ' selected' : '') + (anchor.status === 'edited' ? ' edited' : '');
    el.style.left = frameToX(start) + 'px';
    el.style.width = Math.max(3, frameToX(end - 1) - frameToX(start)) + 'px';
    el.style.top = (laneTop + lane * laneH + 1) + 'px';
    el.style.background = anchor.color || '#55b4ff';
    el.title = `${{anchor.anchor_id}} ${{anchor.start_frame}}-${{anchor.end_frame}} ${{anchor.surface_id || ''}}`;
    el.onclick = (event) => {{ event.stopPropagation(); api('/api/select_anchor', {{anchor_id: anchor.anchor_id, frame: anchor.start_frame}}); }};
    timeline.appendChild(el);
  }});
}}
function scrub(event) {{ api('/api/frame', {{frame: xToFrame(event.clientX)}}); }}
timeline.addEventListener('pointerdown', event => {{ dragging = true; timeline.setPointerCapture(event.pointerId); scrub(event); }});
timeline.addEventListener('pointermove', event => {{ if (dragging) scrub(event); }});
timeline.addEventListener('pointerup', () => {{ dragging = false; }});
timeline.addEventListener('pointercancel', () => {{ dragging = false; }});
document.getElementById('play').onclick = () => api('/api/play', {{playing: !state.playing}});
document.getElementById('prev').onclick = () => api('/api/frame', {{frame: state.current_frame - 1}});
document.getElementById('next').onclick = () => api('/api/frame', {{frame: state.current_frame + 1}});
document.getElementById('save').onclick = () => api('/api/save', {{}});
document.getElementById('discard').onclick = () => api('/api/discard', {{}});
window.addEventListener('keydown', event => {{
  if (!state) return;
  if (event.code === 'Space') {{ event.preventDefault(); api('/api/play', {{playing: !state.playing}}); }}
  if (event.code === 'ArrowLeft') api('/api/frame', {{frame: state.current_frame - (event.shiftKey ? 10 : 1)}});
  if (event.code === 'ArrowRight') api('/api/frame', {{frame: state.current_frame + (event.shiftKey ? 10 : 1)}});
}});
refresh();
setInterval(refresh, 500);
</script>
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
