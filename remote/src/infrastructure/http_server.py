from __future__ import annotations

import base64
import hashlib
import hmac
import json
import select
import secrets
import socket
import threading
from urllib.parse import parse_qs
import time
from dataclasses import replace
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

    STREAM_INTERVAL_SECONDS = 0.5

    def __init__(
        self,
        host: str,
        port: int,
        credentials: RemoteCredentials,
        targets: tuple[RemoteTarget, ...],
        on_sessions_changed: Callable[[], None] | None = None,
        on_remote_message: Callable[[int, str], bool] | None = None,
        get_chat_history: Callable[[int, int, int], tuple[list[dict[str, object]], bool]] | None = None,
        capture_frame: Callable[[int], bytes | None] | None = None,
        get_game_state: Callable[[int], dict[str, object] | None] | None = None,
    ) -> None:
        self._host = host
        self._requested_port = int(port)
        self._credentials = credentials
        self._targets = {target.hwnd: target for target in targets}
        self._on_sessions_changed = on_sessions_changed
        self._on_remote_message = on_remote_message
        self._get_chat_history = get_chat_history
        self._capture_frame = capture_frame
        self._get_game_state = get_game_state
        self._sessions: dict[str, RemoteSession] = {}
        self._lock = threading.RLock()
        self._httpd: _RemoteThreadingHttpServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        httpd = self._httpd
        if httpd is None:
            return ""
        _bound_host, port = httpd.server_address[:2]
        return f"http://{self._advertised_host()}:{port}"

    def _advertised_host(self) -> str:
        """Return a reachable local address instead of the wildcard bind address."""
        if self._host not in {"0.0.0.0", "", "::"}:
            return self._host

        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # UDP connect does not send a packet; it lets the OS select the
            # local interface that would be used for LAN traffic.
            probe.connect(("10.255.255.255", 1))
            address = probe.getsockname()[0]
            if address and not address.startswith("127."):
                return address
        except OSError:
            pass
        finally:
            probe.close()

        try:
            addresses = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for address_info in addresses:
                address = address_info[4][0]
                if address and not address.startswith("127."):
                    return address
        except OSError:
            pass
        return "127.0.0.1"

    def start(self) -> None:
        if self._httpd is not None:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path
                if path == "/status":
                    owner._write_json(self, 200, owner.public_status())
                    return
                session_id, resource = owner._session_resource(path)
                if resource == "stream" and self.headers.get("Upgrade", "").lower() == "websocket":
                    owner._handle_websocket_stream(self, session_id or "")
                    return
                if session_id and resource in {"messages", "frame"}:
                    if resource == "messages":
                        query = parse_qs(parsed.query)
                        try:
                            offset = max(0, int(query.get("offset", ["0"])[0]))
                            limit = max(1, min(10, int(query.get("limit", ["10"])[0])))
                        except (TypeError, ValueError):
                            owner._write_json(self, 400, {"error": "invalid_pagination"})
                            return
                        owner._handle_get_messages(
                            self,
                            session_id,
                            offset,
                            limit,
                        )
                    else:
                        owner._handle_get_frame(self, session_id)
                    return
                owner._write_json(self, 404, {"error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/handshake":
                    owner._handle_handshake(self)
                    return
                if path.startswith("/sessions/") and path.endswith("/target"):
                    session_id = path.removeprefix("/sessions/").removesuffix("/target").strip("/")
                    owner._handle_bind_target(self, session_id)
                    return
                if path.startswith("/sessions/") and path.endswith("/messages"):
                    session_id = path.removeprefix("/sessions/").removesuffix("/messages").strip("/")
                    owner._handle_post_message(self, session_id)
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
                if session.target is not None and session.target.hwnd not in target_map
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
        target = None
        if "target_hwnd" in payload:
            try:
                target_hwnd = int(payload.get("target_hwnd", 0) or 0)
            except (TypeError, ValueError):
                target_hwnd = 0
            with self._lock:
                target = self._targets.get(target_hwnd)
            if target is None or not self._target_matches_payload(target, payload):
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

    def _handle_bind_target(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        if not self._authorize_session(handler, session_id):
            return
        payload = self._read_json(handler)
        if payload is None:
            return
        try:
            target_hwnd = int(payload.get("target_hwnd", 0) or 0)
        except (TypeError, ValueError):
            target_hwnd = 0
        with self._lock:
            session = self._sessions.get(session_id)
            target = self._targets.get(target_hwnd)
            if session is None:
                self._write_json(handler, 404, {"error": "session_not_found"})
                return
            if target is None or not self._target_matches_payload(target, payload):
                self._write_json(handler, 409, {"error": "target_unavailable"})
                return
            bound_session = replace(session, target=target)
            self._sessions[session_id] = bound_session
        self._notify_sessions_changed()
        self._write_json(handler, 200, bound_session.to_dict())

    def _handle_close_session(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        authorization = str(handler.headers.get("Authorization", ""))
        if not hmac.compare_digest(authorization, f"Bearer {session_id}"):
            self._write_json(handler, 401, {"error": "invalid_session"})
            return
        if not self.revoke_session(session_id):
            self._write_json(handler, 404, {"error": "session_not_found"})
            return
        self._write_json(handler, 200, {"closed": True})

    @staticmethod
    def _session_resource(path: str) -> tuple[str | None, str | None]:
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "sessions" and parts[2] in {"messages", "frame", "stream"}:
            return parts[1], parts[2]
        return None, None

    def _handle_websocket_stream(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        session = self._get_bound_session(handler, session_id, "view_stream")
        if session is None:
            return
        key = str(handler.headers.get("Sec-WebSocket-Key", "")).strip()
        if not key:
            self._write_json(handler, 400, {"error": "missing_websocket_key"})
            return
        accept = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
        ).decode("ascii")
        handler.send_response_only(101, "Switching Protocols")
        handler.send_header("Upgrade", "websocket")
        handler.send_header("Connection", "Upgrade")
        handler.send_header("Sec-WebSocket-Accept", accept)
        handler.end_headers()
        handler.wfile.flush()

        connection = handler.connection
        # Keep writes tolerant of normal LAN/mobile jitter. The previous
        # 50ms timeout caused healthy streams to die when one frame took
        # slightly longer to reach a slow client.
        connection.settimeout(5.0)
        last_targets: tuple[tuple[object, ...], ...] | None = None
        last_state_at = 0.0
        frame_sequence = 0
        state_sequence = 0
        try:
            while True:
                with self._lock:
                    live_session = self._sessions.get(session_id)
                    httpd = self._httpd
                    targets = tuple(
                        tuple(target.to_dict().items()) for target in self._targets.values()
                    )
                if httpd is None or live_session is None:
                    self._send_websocket_json(handler, {"type": "session_revoked"})
                    return
                if live_session.target is None:
                    self._send_websocket_json(handler, {"type": "target_unavailable"})
                    return
                if targets != last_targets:
                    self._send_websocket_json(
                        handler,
                        {"type": "targets_changed", "targets": [dict(items) for items in targets]},
                    )
                    last_targets = targets

                try:
                    frame = (
                        self._capture_frame(live_session.target.hwnd)
                        if self._capture_frame
                        else None
                    )
                except Exception as error:
                    self._log_stream_error(session_id, "frame capture", error)
                    frame = None
                if frame:
                    frame_sequence += 1
                    try:
                        self._send_websocket_json(
                            handler,
                            {
                                "type": "frame",
                                "sequence": frame_sequence,
                                "timestamp": time.time(),
                                "mime": "image/jpeg",
                                "size": len(frame),
                            },
                        )
                        self._send_websocket_frame(handler, frame, opcode=2)
                    except (ConnectionError, OSError, BrokenPipeError):
                        raise
                    except Exception as error:
                        self._log_stream_error(session_id, "frame send", error)

                now = time.monotonic()
                if now - last_state_at >= 1.0 and self._get_game_state is not None:
                    try:
                        state = self._get_game_state(live_session.target.hwnd)
                        if state is not None:
                            state_sequence += 1
                            self._send_websocket_json(
                                handler,
                                {
                                    "type": "game_state",
                                    "sequence": state_sequence,
                                    "timestamp": time.time(),
                                    "target_hwnd": live_session.target.hwnd,
                                    "data": state,
                                },
                            )
                    except (ConnectionError, OSError, BrokenPipeError):
                        raise
                    except Exception as error:
                        self._log_stream_error(session_id, "state stream", error)
                    last_state_at = now

                if self._receive_websocket_control(connection):
                    return
                time.sleep(self.STREAM_INTERVAL_SECONDS)
        except (ConnectionError, OSError, BrokenPipeError) as error:
            self._log_stream_error(session_id, "socket closed", error)
            return
        finally:
            connection.settimeout(None)

    @staticmethod
    def _log_stream_error(session_id: str, phase: str, error: BaseException) -> None:
        print(f"[RemoteStream] session={session_id} phase={phase} error={error}")

    @staticmethod
    def _send_websocket_json(handler: BaseHTTPRequestHandler, payload: dict[str, object]) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        RemoteHttpServer._send_websocket_frame(handler, encoded, opcode=1)

    @staticmethod
    def _send_websocket_frame(handler: BaseHTTPRequestHandler, payload: bytes, *, opcode: int) -> None:
        length = len(payload)
        if length < 126:
            header = bytes((0x80 | opcode, length))
        elif length < 65536:
            header = bytes((0x80 | opcode, 126)) + length.to_bytes(2, "big")
        else:
            header = bytes((0x80 | opcode, 127)) + length.to_bytes(8, "big")
        handler.connection.sendall(header + payload)

    @staticmethod
    def _receive_websocket_control(connection: socket.socket) -> bool:
        readable, _, _ = select.select([connection], [], [], 0)
        if not readable:
            return False
        header = connection.recv(2)
        if len(header) < 2:
            return True
        opcode = header[0] & 0x0F
        masked = bool(header[1] & 0x80)
        length = header[1] & 0x7F
        if length == 126:
            length = int.from_bytes(connection.recv(2), "big")
        elif length == 127:
            length = int.from_bytes(connection.recv(8), "big")
        mask = connection.recv(4) if masked else b""
        payload = bytearray(connection.recv(length)) if length else bytearray()
        if masked:
            for index in range(len(payload)):
                payload[index] ^= mask[index % 4]
        if opcode == 8:
            return True
        if opcode == 9:
            RemoteHttpServer._send_websocket_frame_raw(connection, bytes(payload), opcode=10)
        return False

    @staticmethod
    def _send_websocket_frame_raw(connection: socket.socket, payload: bytes, *, opcode: int) -> None:
        length = len(payload)
        if length < 126:
            header = bytes((0x80 | opcode, length))
        elif length < 65536:
            header = bytes((0x80 | opcode, 126)) + length.to_bytes(2, "big")
        else:
            header = bytes((0x80 | opcode, 127)) + length.to_bytes(8, "big")
        connection.sendall(header + payload)

    def _get_bound_session(
        self,
        handler: BaseHTTPRequestHandler,
        session_id: str,
        permission: str,
    ) -> RemoteSession | None:
        if not self._authorize_session(handler, session_id):
            return None
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            self._write_json(handler, 404, {"error": "session_not_found"})
            return None
        if session.target is None:
            self._write_json(handler, 409, {"error": "target_not_selected"})
            return None
        if not session.permissions.get(permission, False):
            self._write_json(handler, 403, {"error": "permission_denied"})
            return None
        return session

    @staticmethod
    def _authorize_session(handler: BaseHTTPRequestHandler, session_id: str) -> bool:
        authorization = str(handler.headers.get("Authorization", ""))
        if not hmac.compare_digest(authorization, f"Bearer {session_id}"):
            RemoteHttpServer._write_json(handler, 401, {"error": "invalid_session"})
            return False
        return True

    @staticmethod
    def _target_matches_payload(target: RemoteTarget, payload: dict[str, object]) -> bool:
        """Validate optional PID/creation-time identity fields when supplied by a client."""
        if "pid" in payload:
            try:
                if int(payload.get("pid") or 0) != target.pid:
                    return False
            except (TypeError, ValueError):
                return False
        if "creation_time" in payload:
            return str(payload.get("creation_time") or "") == target.creation_time
        return True

    def _handle_get_messages(
        self,
        handler: BaseHTTPRequestHandler,
        session_id: str,
        offset: int = 0,
        limit: int = 10,
    ) -> None:
        session = self._get_bound_session(handler, session_id, "connect")
        if session is None:
            return
        callback = self._get_chat_history
        if callback is None:
            self._write_json(handler, 503, {"error": "chat_unavailable"})
            return
        try:
            messages, has_more = callback(session.target.hwnd, offset, min(limit, 10))
        except Exception:
            self._write_json(handler, 500, {"error": "chat_history_failed"})
            return
        self._write_json(handler, 200, {"messages": messages, "has_more": has_more})

    def _handle_post_message(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        session = self._get_bound_session(handler, session_id, "send_chat")
        if session is None:
            return
        payload = self._read_json(handler)
        if payload is None:
            return
        text = str(payload.get("text", "")).strip()
        if not text or len(text) > 8000:
            self._write_json(handler, 400, {"error": "invalid_message"})
            return
        callback = self._on_remote_message
        if callback is None:
            self._write_json(handler, 503, {"error": "chat_unavailable"})
            return
        try:
            accepted = callback(session.target.hwnd, text)
        except Exception:
            self._write_json(handler, 500, {"error": "chat_send_failed"})
            return
        if not accepted:
            self._write_json(handler, 503, {"error": "chat_not_ready"})
            return
        self._write_json(handler, 202, {"accepted": True})

    def _handle_get_frame(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        session = self._get_bound_session(handler, session_id, "view_stream")
        if session is None:
            return
        callback = self._capture_frame
        if callback is None:
            self._write_json(handler, 503, {"error": "stream_unavailable"})
            return
        try:
            frame = callback(session.target.hwnd)
        except Exception:
            self._write_json(handler, 500, {"error": "frame_capture_failed"})
            return
        if not frame:
            self._write_json(handler, 503, {"error": "frame_capture_failed"})
            return
        handler.send_response(200)
        handler.send_header("Content-Type", "image/jpeg")
        handler.send_header("Content-Length", str(len(frame)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(frame)

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
