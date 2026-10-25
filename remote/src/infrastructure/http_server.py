from __future__ import annotations

import hmac
import json
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlparse

from remote.src.domain import DEFAULT_PERMISSIONS, RemoteCredentials, RemoteSession, RemoteTarget


class _RemoteThreadingHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class RemoteHttpServer:
    """Small authenticated HTTP transport for lifecycle and handshake operations."""

    def __init__(
        self,
        host: str,
        port: int,
        credentials: RemoteCredentials,
        targets: tuple[RemoteTarget, ...],
        on_sessions_changed: Callable[[], None] | None = None,
    ) -> None:
        self._host = host
        self._requested_port = int(port)
        self._credentials = credentials
        self._targets = {target.hwnd: target for target in targets}
        self._on_sessions_changed = on_sessions_changed
        self._sessions: dict[str, RemoteSession] = {}
        self._lock = threading.RLock()
        self._httpd: _RemoteThreadingHttpServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        httpd = self._httpd
        if httpd is None:
            return ""
        host, port = httpd.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> None:
        if self._httpd is not None:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/status":
                    owner._write_json(self, 200, owner.public_status())
                    return
                owner._write_json(self, 404, {"error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/handshake":
                    owner._handle_handshake(self)
                    return
                if path.startswith("/sessions/") and path.endswith("/close"):
                    session_id = path.removeprefix("/sessions/").removesuffix("/close").strip("/")
                    owner._handle_close_session(self, session_id)
                    return
                owner._write_json(self, 404, {"error": "not_found"})

            def log_message(self, _format: str, *_args: object) -> None:
                return

        httpd = _RemoteThreadingHttpServer((self._host, self._requested_port), Handler)
        self._httpd = httpd
        self._thread = threading.Thread(
            target=httpd.serve_forever,
            name="remote-http-server",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        httpd, thread = self._httpd, self._thread
        self._httpd = None
        self._thread = None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with self._lock:
            self._sessions.clear()
        self._notify_sessions_changed()

    def set_targets(self, targets: tuple[RemoteTarget, ...]) -> None:
        target_map = {target.hwnd: target for target in targets if target.hwnd}
        changed = False
        with self._lock:
            self._targets = target_map
            stale_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if session.target.hwnd not in target_map
            ]
            for session_id in stale_ids:
                self._sessions.pop(session_id, None)
                changed = True
        if changed:
            self._notify_sessions_changed()

    def sessions(self) -> tuple[RemoteSession, ...]:
        with self._lock:
            return tuple(self._sessions.values())

    def revoke_session(self, session_id: str) -> bool:
        with self._lock:
            removed = self._sessions.pop(str(session_id), None) is not None
        if removed:
            self._notify_sessions_changed()
        return removed

    def public_status(self) -> dict[str, object]:
        with self._lock:
            targets = [target.to_dict() for target in self._targets.values()]
            session_count = len(self._sessions)
        return {
            "status": "running",
            "endpoint": self.endpoint,
            "sessions": session_count,
            "targets": targets,
        }

    def _handle_handshake(self, handler: BaseHTTPRequestHandler) -> None:
        payload = self._read_json(handler)
        if payload is None:
            return
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))
        if not (
            hmac.compare_digest(username, self._credentials.username)
            and hmac.compare_digest(password, self._credentials.password)
        ):
            self._write_json(handler, 401, {"error": "invalid_credentials"})
            return
        try:
            target_hwnd = int(payload.get("target_hwnd", 0) or 0)
        except (TypeError, ValueError):
            target_hwnd = 0
        with self._lock:
            target = self._targets.get(target_hwnd)
        if target is None:
            self._write_json(handler, 409, {"error": "target_unavailable"})
            return
        device_name = str(payload.get("device_name", "Remote device") or "Remote device").strip()[:80]
        session = RemoteSession(
            session_id=secrets.token_urlsafe(18),
            device_name=device_name,
            target=target,
            connected_at=datetime.now(timezone.utc).isoformat(),
            permissions=dict(DEFAULT_PERMISSIONS),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        self._notify_sessions_changed()
        self._write_json(handler, 201, session.to_dict())

    def _handle_close_session(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        authorization = str(handler.headers.get("Authorization", ""))
        if not hmac.compare_digest(authorization, f"Bearer {session_id}"):
            self._write_json(handler, 401, {"error": "invalid_session"})
            return
        if not self.revoke_session(session_id):
            self._write_json(handler, 404, {"error": "session_not_found"})
            return
        self._write_json(handler, 200, {"closed": True})

    def _read_json(self, handler: BaseHTTPRequestHandler) -> dict[str, object] | None:
        try:
            length = int(handler.headers.get("Content-Length", "0") or 0)
            if length <= 0 or length > 64 * 1024:
                raise ValueError("invalid_body_length")
            payload = json.loads(handler.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("invalid_json_object")
            return payload
        except Exception:
            self._write_json(handler, 400, {"error": "invalid_json"})
            return None

    @staticmethod
    def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(encoded)))
        handler.end_headers()
        handler.wfile.write(encoded)

    def _notify_sessions_changed(self) -> None:
        callback = self._on_sessions_changed
        if callback is not None:
            callback()
