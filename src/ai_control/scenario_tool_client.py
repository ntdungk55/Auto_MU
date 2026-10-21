"""Load scenario context and route Gemini calls to discovered MCP tools."""

from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any


_TARGETED_TOOL_CALL_LOCK = threading.RLock()


class ScenarioToolClient:
    """Provide a scenario snapshot and forward Gemini calls to MCP."""

    def __init__(
        self,
        *,
        mcp_client: Any,
        scenario_directory: Path,
    ) -> None:
        self._mcp_client = mcp_client
        self._scenario_directory = scenario_directory
        self._selected_target: tuple[int, int] | None = None

    def start(self) -> None:
        """Start the underlying MCP servers when they are not already running."""
        self._mcp_client.start()

    def stop(self) -> None:
        """Stop the MCP client owned by this chat session."""
        self._mcp_client.stop()

    def refresh_tools(self, timeout_seconds: float = 8.0) -> list[dict[str, Any]]:
        """Return the current MCP ``tools/list`` result."""
        if not self._mcp_client.wait_until_connected(timeout_seconds=timeout_seconds):
            raise RuntimeError(self._mcp_client.status_snapshot().message)
        return self._mcp_client.refresh_tools(timeout_seconds=timeout_seconds)

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Forward one Gemini call while binding the shared MCP selection to this chat tab."""
        clean_name = str(name or "").strip()
        payload = dict(arguments or {})
        # Game-control MCP servers resolve their target from one shared runtime store.
        # Keep selecting and invoking together so another chat tab cannot redirect a call.
        with _TARGETED_TOOL_CALL_LOCK:
            self._synchronize_selected_target()
            return self._text_result_payload(
                self._mcp_client.call_tool(
                    clean_name,
                    payload,
                    timeout_seconds=timeout_seconds,
                )
            )

    def load_scenario_snapshot(self) -> dict[str, Any]:
        """Read the catalog once when a Gemini chat session is created."""
        return self._load_scenario_snapshot()

    def synchronize_selected_target(self, target: Any) -> None:
        """Remember and persist this chat tab's PID/HWND without exposing it to AI."""
        self._selected_target = self._target_identifiers(target)
        with _TARGETED_TOOL_CALL_LOCK:
            self._synchronize_selected_target()

    @staticmethod
    def _target_identifiers(target: Any) -> tuple[int, int]:
        """Validate the process/window identity supplied by the owning chat tab."""
        target_id = str(getattr(target, "target_id", "") or "")
        try:
            process_text, window_text = target_id.split(":", 1)
            return int(process_text), int(window_text)
        except (TypeError, ValueError):
            raise ValueError("selected game target does not contain a valid process id and window handle") from None

    def _synchronize_selected_target(self) -> None:
        """Write this client's saved target to the process store immediately before a call."""
        if self._selected_target is None:
            return
        from src.ai_control.servers.process import select_game_process

        process_id, window_handle = self._selected_target
        result = select_game_process(pid=process_id, selected_window_hwnd=window_handle)
        if not bool(result.get("ok")):
            errors = result.get("errors") or result.get("error") or result
            raise RuntimeError(f"Could not synchronize the selected Gemini target: {errors}")

    def _load_scenario_snapshot(self) -> dict[str, Any]:
        scenarios: list[dict[str, Any]] = []
        if not self._scenario_directory.is_dir():
            return {
                "ok": False,
                "error": f"Scenario directory does not exist: {self._scenario_directory}",
                "scenarios": [],
            }
        for path in sorted(self._scenario_directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(payload, dict):
                    raise ValueError("scenario root must be an object")
                payload["source_file"] = path.name
                scenarios.append(payload)
            except Exception as error:
                scenarios.append({"source_file": path.name, "invalid": True, "error": str(error)})
        return {"ok": True, "scenarios": scenarios, "count": len(scenarios)}

    @staticmethod
    def _text_result_payload(raw_result: dict[str, Any]) -> dict[str, Any]:
        """Read a JSON payload from the standard MCP text-result envelope."""
        for content in raw_result.get("content", []):
            if not isinstance(content, dict) or content.get("type") != "text":
                continue
            try:
                payload = json.loads(str(content.get("text") or ""))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return raw_result
