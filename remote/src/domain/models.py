from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RemoteServerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


DEFAULT_PERMISSIONS: dict[str, bool] = {
    "connect": True,
    "view_stream": True,
    "view_game_state": True,
    "send_chat": True,
    "discover_tools": True,
    "call_readonly_tools": True,
    "call_mutating_tools": True,
}


@dataclass(frozen=True)
class RemoteCredentials:
    username: str
    password: str


@dataclass(frozen=True)
class RemoteTarget:
    hwnd: int
    pid: int
    window_title: str
    process_name: str
    creation_time: str = ""

    @classmethod
    def from_object(cls, target: object) -> "RemoteTarget":
        return cls(
            hwnd=int(getattr(target, "hwnd", 0) or 0),
            pid=int(getattr(target, "pid", getattr(target, "process_id", 0)) or 0),
            window_title=str(getattr(target, "window_title", "") or ""),
            process_name=str(getattr(target, "process_name", "") or ""),
            creation_time=str(getattr(target, "creation_time", "") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hwnd": self.hwnd,
            "pid": self.pid,
            "window_title": self.window_title,
            "process_name": self.process_name,
            "creation_time": self.creation_time,
        }


@dataclass(frozen=True)
class RemoteSession:
    session_id: str
    device_name: str
    target: RemoteTarget
    connected_at: str
    permissions: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_PERMISSIONS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "device_name": self.device_name,
            "target": self.target.to_dict(),
            "connected_at": self.connected_at,
            "permissions": dict(self.permissions),
        }


@dataclass(frozen=True)
class RemoteServerSnapshot:
    state: RemoteServerState
    endpoint: str = ""
    credentials: RemoteCredentials | None = None
    sessions: tuple[RemoteSession, ...] = ()
    targets: tuple[RemoteTarget, ...] = ()
    error: str = ""
