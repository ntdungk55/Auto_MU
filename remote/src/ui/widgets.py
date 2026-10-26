from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from remote.src.application import RemoteServerLifecycleManager
from remote.src.domain import RemoteServerSnapshot, RemoteServerState


_STATE_LABELS = {
    RemoteServerState.STOPPED: "Stopped",
    RemoteServerState.STARTING: "Starting",
    RemoteServerState.RUNNING: "Running",
    RemoteServerState.STOPPING: "Stopping",
    RemoteServerState.ERROR: "Error",
}


def _action_text(snapshot: RemoteServerSnapshot) -> str:
    if snapshot.state == RemoteServerState.RUNNING:
        return "Running — Stop Server"
    if snapshot.state == RemoteServerState.STARTING:
        return "Starting..."
    if snapshot.state == RemoteServerState.STOPPING:
        return "Stopping..."
    if snapshot.state == RemoteServerState.ERROR:
        return "Error — Start Server"
    return "Stopped — Start Server"


def _action_enabled(snapshot: RemoteServerSnapshot) -> bool:
    if snapshot.state == RemoteServerState.RUNNING:
        return True
    return snapshot.state in (RemoteServerState.STOPPED, RemoteServerState.ERROR) and bool(snapshot.targets)


class RemoteServerPanel(QGroupBox):
    open_requested = pyqtSignal()
    toggle_requested = pyqtSignal()

    def __init__(self, manager: RemoteServerLifecycleManager, parent: QWidget | None = None):
        super().__init__("Remote Server", parent)
        self._manager = manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self.status_label = QLabel()
        header.addWidget(self.status_label)
        header.addStretch(1)
        self.open_button = QPushButton("Open Remote Server Status")
        self.open_button.clicked.connect(self.open_requested.emit)
        header.addWidget(self.open_button)
        layout.addLayout(header)

        self.devices_label = QLabel()
        self.devices_label.setWordWrap(True)
        self.devices_label.setStyleSheet("color:#b7bdc8;font-size:11px;")
        layout.addWidget(self.devices_label)

        self.action_button = QPushButton()
        self.action_button.clicked.connect(self.toggle_requested.emit)
        layout.addWidget(self.action_button)

        manager.snapshot_changed.connect(self.apply_snapshot, Qt.ConnectionType.QueuedConnection)
        self.apply_snapshot(manager.snapshot())

    def apply_snapshot(self, snapshot: RemoteServerSnapshot) -> None:
        state_text = _STATE_LABELS[snapshot.state]
        if snapshot.error:
            state_text += f" — {snapshot.error}"
        self.status_label.setText(f"Status: {state_text}")
        color = "#70d68c" if snapshot.state == RemoteServerState.RUNNING else "#ffcf66"
        if snapshot.state == RemoteServerState.ERROR:
            color = "#ff7373"
        self.status_label.setStyleSheet(f"color:{color};font-weight:600;")
        devices = [session.device_name for session in snapshot.sessions]
        if devices:
            self.devices_label.setText("Connected devices: " + ", ".join(devices))
        else:
            self.devices_label.setText("Connected devices: none")
        self.action_button.setText(_action_text(snapshot))
        self.action_button.setEnabled(_action_enabled(snapshot))


class RemoteServerStatusDialog(QDialog):
    toggle_requested = pyqtSignal()

    def __init__(
        self,
        manager: RemoteServerLifecycleManager,
        revoke_session: Callable[[str], bool],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self._revoke_session = revoke_session
        self.setWindowTitle("Remote Server Status")
        self.setMinimumSize(680, 420)
        layout = QVBoxLayout(self)

        self.status_label = QLabel()
        self.endpoint_label = QLabel()
        self.credentials_label = QLabel()
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color:#ff7373;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addWidget(self.endpoint_label)
        layout.addWidget(self.credentials_label)
        layout.addWidget(self.error_label)

        layout.addWidget(QLabel("Active sessions"))
        self.sessions_table = QTableWidget(0, 5)
        self.sessions_table.setHorizontalHeaderLabels(
            ["Device", "Target", "PID / HWND", "Permissions", "Action"]
        )
        self.sessions_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.sessions_table, 1)

        buttons = QHBoxLayout()
        self.action_button = QPushButton()
        self.action_button.clicked.connect(self.toggle_requested.emit)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        buttons.addWidget(self.action_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        manager.snapshot_changed.connect(self.apply_snapshot, Qt.ConnectionType.QueuedConnection)
        self.apply_snapshot(manager.snapshot())

    def apply_snapshot(self, snapshot: RemoteServerSnapshot) -> None:
        self.status_label.setText(f"Status: {_STATE_LABELS[snapshot.state]}")
        self.endpoint_label.setText(f"Endpoint: {snapshot.endpoint or '—'}")
        credentials = snapshot.credentials
        if credentials is None:
            self.credentials_label.setText("Username: —    Password: —")
        else:
            self.credentials_label.setText(
                f"Username: {credentials.username}    Password: {credentials.password}"
            )
        self.error_label.setText(snapshot.error)
        self.error_label.setVisible(bool(snapshot.error))
        self.action_button.setText(_action_text(snapshot))
        self.action_button.setEnabled(_action_enabled(snapshot))

        self.sessions_table.setRowCount(len(snapshot.sessions))
        for row, session in enumerate(snapshot.sessions):
            self.sessions_table.setItem(row, 0, QTableWidgetItem(session.device_name))
            target = session.target
            self.sessions_table.setItem(
                row,
                1,
                QTableWidgetItem(target.window_title if target is not None else "Selecting window"),
            )
            self.sessions_table.setItem(
                row,
                2,
                QTableWidgetItem(
                    f"{target.pid} / {target.hwnd}" if target is not None else "—"
                ),
            )
            enabled_count = sum(1 for enabled in session.permissions.values() if enabled)
            self.sessions_table.setItem(
                row,
                3,
                QTableWidgetItem(f"{enabled_count}/{len(session.permissions)} enabled"),
            )
            revoke_button = QPushButton("Revoke")
            revoke_button.clicked.connect(
                lambda _checked=False, session_id=session.session_id: self._revoke_session(session_id)
            )
            self.sessions_table.setCellWidget(row, 4, revoke_button)
        self.sessions_table.resizeColumnsToContents()


class RemoteLifecycleDialog(QDialog):
    cancel_requested = pyqtSignal()

    def __init__(self, state: RemoteServerState, parent: QWidget | None = None):
        super().__init__(parent)
        self._finishing = False
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowTitle("Remote Server")
        layout = QVBoxLayout(self)
        self.message = QLabel()
        self.message.setMinimumWidth(380)
        layout.addWidget(self.message)
        row = QHBoxLayout()
        row.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.set_state(state)

    def set_state(self, state: RemoteServerState) -> None:
        action = "Starting" if state == RemoteServerState.STARTING else "Stopping"
        self.setWindowTitle(f"{action} Remote Server")
        self.message.setText(f"{action} Remote Server...\nToàn bộ AI Chat đang bị khóa.")

    def finish(self) -> None:
        self._finishing = True
        self.accept()

    def closeEvent(self, event) -> None:
        if not self._finishing:
            self.cancel_requested.emit()
            event.ignore()
            return
        super().closeEvent(event)
