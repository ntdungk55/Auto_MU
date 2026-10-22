"""Atomic persistence for the process selected by the Process MCP server."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any

from src.logic.app_paths import get_runtime_root


class SelectedProcessStore:
    """Read and atomically replace the cross-server selected-process snapshot."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path(get_runtime_root()) / "runtime" / "selected_process.json"
        self._lock = threading.RLock()

    def load(self) -> dict[str, Any] | None:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                return None
            except (OSError, UnicodeError, json.JSONDecodeError):
                return None
        return payload if isinstance(payload, dict) else None

    def save(self, selection: dict[str, Any]) -> None:
        payload = dict(selection)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.path.parent,
                    prefix=f".{self.path.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temp_path = Path(handle.name)
                os.replace(temp_path, self.path)
            finally:
                if temp_path is not None and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass

    def clear(self) -> None:
        with self._lock:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


selected_process_store = SelectedProcessStore()

