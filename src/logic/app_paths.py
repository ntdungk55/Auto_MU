"""Shared paths for runtime data used by both source and frozen builds."""

from __future__ import annotations

import os
import sys


def get_runtime_root() -> str:
    """Return the directory that owns mutable runtime data.

    A frozen build stores data beside ``TestAuto.exe``. Source runs use the
    project's ``build`` directory so both launch modes share the same files.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(project_root, "build")


def get_app_state_path() -> str:
    """Return the single app_state.json path and ensure its directory exists."""
    runtime_root = get_runtime_root()
    os.makedirs(runtime_root, exist_ok=True)
    return os.path.join(runtime_root, "app_state.json")
