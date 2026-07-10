from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from motion_edit.workbench.session import WorkbenchSession


def make_workbench_server(session: WorkbenchSession, *, host: str = "127.0.0.1", port: int = 8095) -> ThreadingHTTPServer:
    class WorkbenchHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/state":
                self._send_json(session.state())
                return
            self._send_json({"error": f"unknown endpoint: {path}"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                body = self._read_json()
                if path == "/api/select":
                    payload = session.set_selection(
                        motion_id=body.get("motion_id"),
                        segment_id=body.get("segment_id"),
                        index=body.get("index"),
                        current_frame=body.get("current_frame"),
                    )
                elif path == "/api/trim":
                    payload = session.trim(
                        start_frame=int(body["start_frame"]),
                        end_frame=int(body["end_frame"]),
                        output_source=body.get("output_source"),
                    )
                elif path == "/api/split":
                    payload = session.split(frame=int(body["frame"]), output_source=body.get("output_source"))
                elif path == "/api/accept":
                    payload = session.accept(output_source=body.get("output_source"))
                elif path == "/api/reject":
                    payload = session.reject(output_source=body.get("output_source"))
                else:
                    self._send_json({"error": f"unknown endpoint: {path}"}, status=404)
                    return
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(payload)

        def log_message(self, _format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer((host, int(port)), WorkbenchHandler)
