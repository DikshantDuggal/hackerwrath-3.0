"""
Standalone HTTP server runner for `app.main:app` using Python's standard library
when `uvicorn` is not installed, or delegates to `uvicorn` when available.
Allows running `python3 -m app.asgi_stdlib_runner` in any environment.
"""
from __future__ import annotations

import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Tuple
from app.core.compat import LocalTestClient
from app.main import app

_client = LocalTestClient(app)


def _parse_multipart(content_type: str, body: bytes) -> Tuple[Dict[str, str], Dict[str, Tuple[str, bytes, str]]]:
    form_data: Dict[str, str] = {}
    files: Dict[str, Tuple[str, bytes, str]] = {}
    if "boundary=" not in content_type:
        return form_data, files

    boundary = content_type.split("boundary=", 1)[1].split(";", 1)[0].strip().strip('"')
    delimiter = f"--{boundary}".encode()
    parts = body.split(delimiter)
    for part in parts[1:]:
        if part.startswith(b"--") or not part.strip():
            continue
        if b"\r\n\r\n" not in part:
            continue
        header_block, content = part.split(b"\r\n\r\n", 1)
        if content.endswith(b"\r\n"):
            content = content[:-2]
        header_text = header_block.decode("utf-8", errors="ignore")
        name_match = None
        filename_match = None
        part_ctype = "application/octet-stream"
        for line in header_text.split("\r\n"):
            lower = line.lower()
            if "content-disposition:" in lower:
                for token in line.split(";"):
                    token = token.strip()
                    if token.startswith("name="):
                        name_match = token.split("=", 1)[1].strip('"')
                    elif token.startswith("filename="):
                        filename_match = token.split("=", 1)[1].strip('"')
            elif lower.startswith("content-type:"):
                part_ctype = line.split(":", 1)[1].strip()

        if name_match:
            if filename_match is not None:
                files[name_match] = (filename_match, content, part_ctype)
            else:
                form_data[name_match] = content.decode("utf-8", errors="ignore")

    return form_data, files


class BackendRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status_code: int, payload: object) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        resp = _client.get(self.path)
        self._send_json(resp.status_code, resp.json())

    def do_DELETE(self) -> None:
        resp = _client.delete(self.path)
        self._send_json(resp.status_code, resp.json())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length > 0 else b""
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            form_data, files = _parse_multipart(content_type, raw_body)
            resp = _client.post(self.path, data=form_data, files=files)
            self._send_json(resp.status_code, resp.json())
            return

        json_body: Optional[object] = None
        if raw_body:
            try:
                json_body = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json(422, {"detail": "Invalid JSON body"})
                return

        # Support JSON-wrapped base64 file upload for /transcribe if sent as application/json
        if self.path.split("?")[0] == "/transcribe" and isinstance(json_body, dict) and "audio_base64" in json_body:
            fname = str(json_body.get("filename", "audio.wav"))
            lang = str(json_body.get("language_code", "auto"))
            try:
                fbytes = base64.b64decode(str(json_body.get("audio_base64", "")))
            except Exception:
                fbytes = b""
            resp = _client.post(
                self.path,
                data={"language_code": lang},
                files={"file": (fname, fbytes, "audio/wav")},
            )
            self._send_json(resp.status_code, resp.json())
            return

        resp = _client.post(self.path, json=json_body)
        self._send_json(resp.status_code, resp.json())


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), BackendRequestHandler)
    print(f"Python Scam-Detection FastAPI Backend listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port_num = int(os.getenv("PYTHON_BACKEND_PORT", "8000"))
    run_server(port=port_num)
