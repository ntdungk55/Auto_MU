from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, pyqtSignal

from remote.src.domain import RemoteServerSnapshot, RemoteServerState, RemoteTarget
from remote.src.infrastructure import RemoteHttpServer
from remote.src.logic import generate_credentials


class RemoteServerLifecycleManager(QObject):
    """Own the one shared server and expose thread-safe lifecycle snapshots to Qt."""

    snapshot_changed = pyqtSignal(object)
    state_changed = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None, *, host: str = "127.0.0.1", port: int = 8765):
        super().__init__(parent)
        self._host = str(host)
        self._port = int(port)
        self._lock = threading.RLock()
        self._state = RemoteServerState.STOPPED
        self._error = ""
        self._targets: tuple[RemoteTarget, ...] = ()
        self._credentials = None
        self._server: RemoteHttpServer | None = None
        self._operation_cancel: threading.Event | None = None
        self._operation_thread: threading.Thread | None = None

    @property
    def state(self) -> RemoteServerState:
        with self._lock:
            return self._state

    def snapshot(self) -> RemoteServerSnapshot:
        with self._lock:
            server = self._server
            return RemoteServerSnapshot(
                state=self._state,
                endpoint=server.endpoint if server is not None else "",
                credentials=self._credentials if self._state == RemoteServerState.RUNNING else None,
                sessions=server.sessions() if server is not None else (),
                targets=self._targets,
                error=self._error,
            )

    def set_targets(self, targets: list[object] | tuple[object, ...]) -> None:
        normalized: dict[int, RemoteTarget] = {}
        for target_object in targets:
            target = RemoteTarget.from_object(target_object)
            if target.hwnd:
                normalized[target.hwnd] = target
        with self._lock:
            self._targets = tuple(normalized.values())
            server = self._server
        if server is not None:
            server.set_targets(self._targets)
        self._publish_snapshot()

    def start(self) -> bool:
        with self._lock:
            if self._state not in (RemoteServerState.STOPPED, RemoteServerState.ERROR):
                return False
            if not self._targets:
                self._error = "Hãy chọn ít nhất một game window trước khi khởi động Remote Server."
                self._publish_snapshot_locked()
                return False
            self._state = RemoteServerState.STARTING
            self._error = ""
            cancel_event = threading.Event()
            self._operation_cancel = cancel_event
            worker = threading.Thread(
                target=self._run_start,
                args=(cancel_event,),
                name="remote-server-start",
                daemon=True,
            )
            self._operation_thread = worker
            self._publish_snapshot_locked()
        worker.start()
        return True

    def stop(self) -> bool:
        with self._lock:
            if self._state != RemoteServerState.RUNNING or self._server is None:
                return False
            self._state = RemoteServerState.STOPPING
            self._error = ""
            cancel_event = threading.Event()
            self._operation_cancel = cancel_event
            worker = threading.Thread(
                target=self._run_stop,
                args=(cancel_event,),
                name="remote-server-stop",
                daemon=True,
            )
            self._operation_thread = worker
            self._publish_snapshot_locked()
        worker.start()
        return True

    def cancel_operation(self) -> bool:
        with self._lock:
            if self._state not in (RemoteServerState.STARTING, RemoteServerState.STOPPING):
                return False
            cancel_event = self._operation_cancel
        if cancel_event is not None:
            cancel_event.set()
            return True
        return False

    def revoke_session(self, session_id: str) -> bool:
        with self._lock:
            server = self._server
        return bool(server and server.revoke_session(session_id))

    def shutdown(self) -> None:
        with self._lock:
            cancel_event = self._operation_cancel
            server = self._server
            self._server = None
            self._operation_cancel = None
            self._operation_thread = None
            self._credentials = None
            self._state = RemoteServerState.STOPPED
            self._error = ""
        if cancel_event is not None:
            cancel_event.set()
        if server is not None:
            server.stop()
        self._publish_snapshot()

    def _run_start(self, cancel_event: threading.Event) -> None:
        credentials = generate_credentials()
        with self._lock:
            targets = self._targets
        server = RemoteHttpServer(
            self._host,
            self._port,
            credentials,
            targets,
            on_sessions_changed=self._publish_snapshot,
        )
        try:
            # Keep a brief cancellable phase before binding the socket so the UI's
            # Cancel Start action is meaningful even on a fast local machine.
            if cancel_event.wait(0.2):
                self._finish_cancelled_start()
                return
            server.start()
            if cancel_event.is_set():
                server.stop()
                self._finish_cancelled_start()
                return
            with self._lock:
                self._server = server
                self._credentials = credentials
                self._state = RemoteServerState.RUNNING
                self._operation_cancel = None
                self._operation_thread = None
                self._error = ""
                self._publish_snapshot_locked()
        except Exception as error:
            try:
                server.stop()
            except Exception:
                pass
            self._finish_error(str(error))

    def _run_stop(self, cancel_event: threading.Event) -> None:
        # A short cancellable phase guarantees that Cancel Stop can preserve live sessions.
        if cancel_event.wait(0.35):
            with self._lock:
                if (
                    self._operation_cancel is not cancel_event
                    or self._state != RemoteServerState.STOPPING
                ):
                    return
                self._state = RemoteServerState.RUNNING
                self._operation_cancel = None
                self._operation_thread = None
                self._publish_snapshot_locked()
            return
        with self._lock:
            if (
                self._operation_cancel is not cancel_event
                or self._state != RemoteServerState.STOPPING
            ):
                return
            server = self._server
        try:
            if server is not None:
                server.stop()
            with self._lock:
                self._server = None
                self._credentials = None
                self._state = RemoteServerState.STOPPED
                self._operation_cancel = None
                self._operation_thread = None
                self._error = ""
                self._publish_snapshot_locked()
        except Exception as error:
            self._finish_error(str(error))

    def _finish_cancelled_start(self) -> None:
        with self._lock:
            self._server = None
            self._credentials = None
            self._state = RemoteServerState.STOPPED
            self._operation_cancel = None
            self._operation_thread = None
            self._error = ""
            self._publish_snapshot_locked()

    def _finish_error(self, message: str) -> None:
        with self._lock:
            self._server = None
            self._credentials = None
            self._state = RemoteServerState.ERROR
            self._operation_cancel = None
            self._operation_thread = None
            self._error = message or "Remote Server operation failed."
            self._publish_snapshot_locked()

    def _publish_snapshot(self) -> None:
        snapshot = self.snapshot()
        self.snapshot_changed.emit(snapshot)
        self.state_changed.emit(snapshot.state.value)
    def _publish_snapshot_locked(self) -> None:
        server = self._server
        snapshot = RemoteServerSnapshot(
            state=self._state,
            endpoint=server.endpoint if server is not None else "",
            credentials=self._credentials if self._state == RemoteServerState.RUNNING else None,
            sessions=server.sessions() if server is not None else (),
            targets=self._targets,
            error=self._error,
        )
        self.snapshot_changed.emit(snapshot)
        self.state_changed.emit(snapshot.state.value)

