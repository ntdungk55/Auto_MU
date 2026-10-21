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


def get_tools_root() -> str:
    """Return the mutable runtime directory for saved tool definitions."""
    return os.path.join(get_runtime_root(), "tools")


def get_images_root() -> str:
    """Return the application image root without changing the process cwd."""
    return os.path.join(get_runtime_root(), "images")


def get_assets_root() -> str:
    """Return the application-managed resource root."""
    if getattr(sys, "frozen", False):
        return os.path.join(get_runtime_root(), "assets")

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(project_root, "assets")


def get_teaching_root() -> str:
    """Return the managed root for tool teaching assets."""
    return os.path.join(get_assets_root(), "teaching")


def get_algorithm_testing_root() -> str:
    """Return the mutable root for algorithm-testing sessions and captures."""
    return os.path.join(get_images_root(), "algorithm_testing")


def get_scenario_engine_root() -> str:
    """Return the bundled scenario-engine resource directory."""
    return os.path.join(get_assets_root(), "scenario_engine")


def get_tool_teaching_dir(tool_id: str | None) -> str:
    """Return a stable per-tool teaching directory."""
    return os.path.join(get_teaching_root(), str(tool_id or "default"))
