"""JSON settings persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsStore:
    """Load and save non-secret sample settings as UTF-8 JSON."""

    def load(self, path: Path) -> dict[str, Any]:
        """Load one JSON configuration file."""
        with path.open("r", encoding="utf-8-sig") as stream:
            return json.load(stream)

    def save(self, path: Path, settings: dict[str, Any]) -> None:
        """Save one JSON configuration file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(settings, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
