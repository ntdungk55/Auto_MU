"""Persistent JSON repository for scenarios."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..domain.scenario import Scenario


class ScenarioRepository:
    """Store scenarios in one versioned runtime JSON document."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self.default_path()

    @staticmethod
    def default_path() -> Path:
        """Return the application-data path without using sample configuration files."""
        base_path = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return base_path / "AutoMU" / "ai_game_controller" / "scenarios.json"

    def list_for_target(self, target_id: str) -> tuple[Scenario, ...]:
        """Return scenarios belonging to one target."""
        payload = self._load_payload()
        return tuple(
            Scenario.from_dict(item)
            for item in payload["scenarios"]
            if item.get("targetId") == target_id
        )

    def get(self, target_id: str, scenario_id: str) -> Scenario | None:
        """Return a target-scoped scenario by its identifier."""
        return next(
            (
                scenario
                for scenario in self.list_for_target(target_id)
                if scenario.scenario_id == scenario_id
            ),
            None,
        )

    def save(self, scenario: Scenario) -> None:
        """Create or replace one scenario and atomically persist the document."""
        payload = self._load_payload()
        scenarios = [
            item
            for item in payload["scenarios"]
            if not (item.get("targetId") == scenario.target_id and item.get("id") == scenario.scenario_id)
        ]
        scenarios.append(scenario.to_dict())
        payload["scenarios"] = scenarios
        self._save_payload(payload)

    def delete(self, target_id: str, scenario_id: str) -> bool:
        """Delete a scenario and return whether a persisted item was removed."""
        payload = self._load_payload()
        scenarios = payload["scenarios"]
        updated = [
            item
            for item in scenarios
            if not (item.get("targetId") == target_id and item.get("id") == scenario_id)
        ]
        if len(updated) == len(scenarios):
            return False
        payload["scenarios"] = updated
        self._save_payload(payload)
        return True

    def _load_payload(self) -> dict[str, object]:
        if not self.path.exists():
            return {"schemaVersion": 1, "scenarios": []}
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                payload = json.load(stream)
        except (OSError, json.JSONDecodeError):
            return {"schemaVersion": 1, "scenarios": []}
        scenarios = payload.get("scenarios") if isinstance(payload, dict) else None
        if not isinstance(scenarios, list):
            return {"schemaVersion": 1, "scenarios": []}
        return {"schemaVersion": 1, "scenarios": scenarios}

    def _save_payload(self, payload: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f"{self.path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                temporary_path = Path(stream.name)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)
