"""Scenario lifecycle orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock

from .ai_agent import AIAgent, AIRequest, AIResponse
from .prompt_builder import PromptBuilder
from ..domain.game_event import GameEvent
from ..domain.scenario import Scenario


EventListener = Callable[[GameEvent], None]
AIResponseListener = Callable[[GameEvent, AIResponse], None]


class ScenarioEngine:
    """Turn detected events into provider-neutral AI requests and responses."""

    def __init__(self, prompt_builder: PromptBuilder, ai_agent: AIAgent, system_prompt: str) -> None:
        self._prompt_builder = prompt_builder
        self._ai_agent = ai_agent
        self._system_prompt = system_prompt
        self._event_listeners: set[EventListener] = set()
        self._response_listeners: set[AIResponseListener] = set()
        self._lock = RLock()

    def subscribe(self, listener: EventListener) -> None:
        """Register one caller that wants to receive future game events."""
        with self._lock:
            self._event_listeners.add(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """Remove one event listener without affecting other listeners."""
        with self._lock:
            self._event_listeners.discard(listener)

    def subscribe_response(self, listener: AIResponseListener) -> None:
        """Register one caller that wants future AI responses for game events."""
        with self._lock:
            self._response_listeners.add(listener)

    def unsubscribe_response(self, listener: AIResponseListener) -> None:
        """Remove one AI-response listener."""
        with self._lock:
            self._response_listeners.discard(listener)

    def handle_events(self, scenario: Scenario | None, events: list[GameEvent]) -> None:
        """Notify event listeners and submit enabled events to the configured AI agent."""
        if not events:
            return
        with self._lock:
            event_listeners = tuple(self._event_listeners)
            response_listeners = tuple(self._response_listeners)
        for event in events:
            self._notify_event_listeners(event_listeners, event)
            if scenario is None or scenario.target_id != event.target_id:
                continue
            if scenario.enabled_events and event.event_type not in scenario.enabled_events:
                continue
            response = self._request_ai(scenario, event)
            self._notify_response_listeners(response_listeners, event, response)

    def _request_ai(self, scenario: Scenario, event: GameEvent) -> AIResponse:
        prompt = self._prompt_builder.build(self._system_prompt, scenario, event)
        try:
            return self._ai_agent.respond(
                AIRequest(system_prompt=self._system_prompt, prompt=prompt, target_id=event.target_id)
            )
        except Exception as error:
            return AIResponse(
                text="",
                model_name="",
                created_at=datetime.now(timezone.utc),
                error=str(error),
            )

    @staticmethod
    def _notify_event_listeners(listeners: tuple[EventListener, ...], event: GameEvent) -> None:
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                continue

    @staticmethod
    def _notify_response_listeners(
        listeners: tuple[AIResponseListener, ...],
        event: GameEvent,
        response: AIResponse,
    ) -> None:
        for listener in listeners:
            try:
                listener(event, response)
            except Exception:
                continue
