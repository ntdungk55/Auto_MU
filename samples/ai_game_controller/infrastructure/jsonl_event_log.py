"""JSON Lines event logging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlEventLog:
    """Append structured runtime records without storing secrets."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        """Append one compact JSON object as one line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")
