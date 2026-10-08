"""Persistent, character-scoped chat history with weekly retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import threading
from typing import Any


class ChatMessageLog:
    """Store chat turns on disk and return bounded pages for the UI."""

    RETENTION_DAYS = 7
    PAGE_TURNS = 5

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2] / "chat_message_log"
        self._lock = threading.RLock()

    @staticmethod
    def character_key(window_title: str) -> str:
        """Return a filesystem-safe character key from a game window title."""
        match = re.search(r"\([^)]*-[^)]*?\s+([^)]+)\)", str(window_title or ""))
        value = match.group(1).strip() if match else str(window_title or "Game")
        value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("._")
        return value or "Game"

    def purge_expired(self, now: datetime | None = None) -> None:
        """Remove message records older than the rolling seven-day window."""
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=self.RETENTION_DAYS)
        with self._lock:
            if not self.root.exists():
                return
            for character_dir in tuple(path for path in self.root.iterdir() if path.is_dir()):
                for path in tuple(character_dir.glob("*.jsonl")):
                    records = [record for record in self._read_file(path) if self._record_time(record) >= cutoff]
                    if records:
                        self._write_file(path, records)
                    else:
                        path.unlink(missing_ok=True)
                if not any(character_dir.iterdir()):
                    character_dir.rmdir()

    def append(self, character_key: str, record: dict[str, Any]) -> None:
        """Append one chat message without blocking the UI on a full cleanup scan."""
        timestamp = str(record.get("timestamp") or datetime.now(timezone.utc).isoformat())
        value = {**record, "timestamp": timestamp}
        date_name = self._record_time(value).date().isoformat()
        path = self.root / self._safe_key(character_key) / f"{date_name}.jsonl"
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")

    def load_turn_page(
        self,
        character_key: str,
        offset: int = 0,
        limit: int = PAGE_TURNS,
    ) -> tuple[list[list[dict[str, Any]]], bool]:
        """Load a page of complete turns, newest page first, for UI rendering."""
        with self._lock:
            records = self._read_character(character_key)
        turns: list[list[dict[str, Any]]] = []
        by_id: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            turn_id = str(record.get("turn_id") or f"legacy-{len(turns)}")
            if turn_id not in by_id:
                by_id[turn_id] = []
                turns.append(by_id[turn_id])
            by_id[turn_id].append(record)
        end = max(0, len(turns) - max(0, int(offset)))
        start = max(0, end - max(1, int(limit)))
        return turns[start:end], start > 0

    def _read_character(self, character_key: str) -> list[dict[str, Any]]:
        directory = self.root / self._safe_key(character_key)
        if not directory.exists():
            return []
        records = [record for path in sorted(directory.glob("*.jsonl")) for record in self._read_file(path)]
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.RETENTION_DAYS)
        return [record for record in records if self._record_time(record) >= cutoff]

    @staticmethod
    def _read_file(path: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    value = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(value, dict):
                    records.append(value)
        except OSError:
            return []
        return records

    @staticmethod
    def _write_file(path: Path, records: list[dict[str, Any]]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records),
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _record_time(record: dict[str, Any]) -> datetime:
        try:
            value = datetime.fromisoformat(str(record.get("timestamp", "")).replace("Z", "+00:00"))
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    @staticmethod
    def _safe_key(value: str) -> str:
        return re.sub(r"[^\w.-]+", "_", str(value or "Game"), flags=re.UNICODE).strip("._") or "Game"
