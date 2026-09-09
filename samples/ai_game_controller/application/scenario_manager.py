"""Scenario CRUD use cases."""

from __future__ import annotations

from ..domain.scenario import Scenario
from ..infrastructure.scenario_repository import ScenarioRepository


class ScenarioManager:
    """Validate and persist scenarios scoped to one game target."""

    def __init__(self, repository: ScenarioRepository) -> None:
        self._repository = repository

    def list_for_target(self, target_id: str) -> tuple[Scenario, ...]:
        """Return all scenarios saved for one target."""
        return self._repository.list_for_target(target_id)

    def get(self, target_id: str, scenario_id: str) -> Scenario | None:
        """Return one scenario when it belongs to the requested target."""
        return self._repository.get(target_id, scenario_id)

    def save(self, scenario: Scenario) -> Scenario:
        """Create or update one valid scenario."""
        self._validate(scenario)
        self._repository.save(scenario)
        return scenario

    def delete(self, target_id: str, scenario_id: str) -> bool:
        """Delete one saved scenario without changing an active runtime snapshot."""
        return self._repository.delete(target_id, scenario_id)

    @staticmethod
    def _validate(scenario: Scenario) -> None:
        if not scenario.scenario_id.strip():
            raise ValueError("scenario_id must not be empty")
        if not scenario.target_id.strip():
            raise ValueError("target_id must not be empty")
        if not scenario.name.strip():
            raise ValueError("scenario name must not be empty")
        if not scenario.instruction.strip():
            raise ValueError("scenario instruction must not be empty")
