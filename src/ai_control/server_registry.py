"""Registry of MCP servers started with the Auto_MU application."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class MCPServerSpec:
    name: str
    command: str
    args: tuple[str, ...]
    cwd: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_server_specs() -> list[MCPServerSpec]:
    """Return every MCP server that should start with the application."""
    if getattr(sys, "frozen", False):
        executable = os.path.abspath(sys.executable)
        cwd = os.path.dirname(executable)
        return [
            MCPServerSpec("keyboard", executable, ("--mcp-keyboard-server",), cwd),
            MCPServerSpec("game_state", executable, ("--mcp-game-state-server",), cwd),
            MCPServerSpec("notifications", executable, ("--mcp-notifications-server",), cwd),
        ]

    root = project_root()
    return [
        MCPServerSpec(
            "keyboard",
            sys.executable,
            (str(root / "mcp" / "keyboard" / "server.py"),),
            str(root),
        ),
        MCPServerSpec(
            "game_state",
            sys.executable,
            (str(root / "mcp" / "game_state" / "server.py"),),
            str(root),
        ),
        MCPServerSpec(
            "notifications",
            sys.executable,
            (str(root / "mcp" / "notifications" / "server.py"),),
            str(root),
        ),
    ]
