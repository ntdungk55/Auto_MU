from __future__ import annotations

from collections import deque

import pytest

from src.ai_control.ai_models.contracts import (
    AIChatSession,
    AIModelAdapter,
    AIResponse,
    AIToolCall,
    AIToolResult,
    AIUsage,
)
from src.ai_control.ai_models.factory import AIModelFactory
from src.ai_control.ai_manager import AIManager


class _StatusError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class _FakeSession(AIChatSession):
    def __init__(self, outcomes: deque[object]) -> None:
        self._outcomes = outcomes

    @property
    def history(self):
        return []

    def send(self, content):
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def send_tool_results(self, results: list[AIToolResult]):
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeAdapter(AIModelAdapter):
    def __init__(self, *, model_name: str, outcomes: deque[object], calls: list[str], **_: object) -> None:
        self._model_name = model_name
        self._outcomes = outcomes
        self._calls = calls

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return self._model_name

    def validate(self):
        return None

    def start_chat(self, *, system_prompt, tools, history=None):
        self._calls.append(self._model_name)
        return _FakeSession(self._outcomes)


def _manager(*, retries=0, clock=lambda: 100.0):
    factory = AIModelFactory()
    factory.register("fake", _FakeAdapter)
    return AIManager(
        factory,
        max_retries_per_model=retries,
        clock=clock,
        sleep=lambda _: None,
    )


def _register(manager, model_id, level, outcomes, calls, **kwargs):
    api_key = kwargs.pop("api_key", None)
    adapter_config = {"outcomes": deque(outcomes), "calls": calls}
    if api_key is not None:
        adapter_config["api_key"] = api_key
    manager.register_model(
        model_id,
        provider="fake",
        model_name=model_id,
        intelligence_level=level,
        adapter_config=adapter_config,
        **kwargs,
    )


def test_manager_routes_easy_and_hard_requests_to_matching_model_strength():
    calls = []
    manager = _manager()
    _register(manager, "small", 1, [AIResponse(text="small")], calls)
    _register(manager, "large", 3, [AIResponse(text="large")], calls)

    easy = manager.execute("attack or heal?", system_prompt="system", difficulty=1)
    hard = manager.execute("recover from repeated failures", system_prompt="system", difficulty=3)

    assert easy.text == "small"
    assert hard.text == "large"
    assert calls == ["small", "large"]


def test_manager_filters_tools_context_and_quota_before_calling_provider():
    calls = []
    manager = _manager()
    _register(manager, "no-tools", 1, [AIResponse(text="wrong")], calls, supports_tools=False)
    _register(manager, "low-quota", 1, [AIResponse(text="wrong")], calls, token_quota=100)
    _register(manager, "eligible", 1, [AIResponse(text="ok")], calls, token_quota=10_000)

    result = manager.execute(
        "choose a tool",
        system_prompt="system",
        tools=[{"name": "attack", "input_schema": {"type": "object"}}],
    )

    assert result.text == "ok"
    assert calls == ["eligible"]


def test_manager_falls_back_and_cools_down_rate_limited_deployment():
    calls = []
    manager = _manager()
    _register(manager, "primary", 1, [_StatusError(429, "rate limit")], calls, priority=2)
    _register(manager, "fallback", 1, [AIResponse(text="fallback")], calls)

    result = manager.execute("hello", system_prompt="system")
    statuses = {item["id"]: item for item in manager.model_status()}

    assert result.text == "fallback"
    assert calls == ["primary", "fallback"]
    assert statuses["primary"]["healthy"] is False
    assert statuses["primary"]["failures"] == 1


def test_manager_retries_transient_failure_once_before_fallback():
    calls = []
    manager = _manager(retries=1)
    _register(
        manager,
        "primary",
        1,
        [TimeoutError("slow"), AIResponse(text="recovered")],
        calls,
        priority=2,
    )
    _register(manager, "fallback", 1, [AIResponse(text="fallback")], calls)

    result = manager.execute("hello", system_prompt="system")

    assert result.text == "recovered"
    assert calls == ["primary", "primary"]


def test_manager_reconciles_reported_usage_and_never_exposes_credentials():
    calls = []
    manager = _manager()
    _register(
        manager,
        "metered",
        1,
        [AIResponse(text="ok", usage=AIUsage(input_tokens=70, output_tokens=30, total_tokens=100))],
        calls,
        token_quota=2_000,
        api_key="secret",
    )

    manager.execute("hello", system_prompt="system")
    status = manager.model_status()[0]

    assert status["remaining_tokens"] == 1_900
    assert status["used_tokens"] == 100
    assert status["reserved_tokens"] == 0
    assert "adapter_config" not in status
    assert "secret" not in repr(status)


def test_manager_disables_bad_credentials_and_uses_next_deployment():
    calls = []
    manager = _manager()
    _register(manager, "bad-auth", 1, [_StatusError(401, "invalid key")], calls, priority=2)
    _register(manager, "fallback", 1, [AIResponse(text="ok")], calls)

    assert manager.execute("hello", system_prompt="system").text == "ok"
    statuses = {item["id"]: item for item in manager.model_status()}

    assert statuses["bad-auth"]["enabled"] is False
    assert calls == ["bad-auth", "fallback"]


def test_manager_does_not_fallback_for_invalid_request():
    calls = []
    manager = _manager()
    _register(manager, "first", 1, [_StatusError(400, "invalid tools")], calls, priority=2)
    _register(manager, "second", 1, [AIResponse(text="should not run")], calls)

    with pytest.raises(_StatusError):
        manager.execute("hello", system_prompt="system")

    assert calls == ["first"]


def test_managed_chat_falls_back_on_first_send_and_exposes_active_model():
    calls = []
    manager = _manager()
    _register(manager, "primary", 1, [_StatusError(429, "rate limit")], calls, priority=2)
    _register(manager, "fallback", 1, [AIResponse(text="ok")], calls)

    chat = manager.start_chat(system_prompt="system", tools=[])
    response = chat.send("hello")

    assert response.text == "ok"
    assert chat.active_model_id == "fallback"
    assert calls == ["primary", "fallback"]


def test_managed_chat_keeps_provider_pinned_during_tool_loop():
    calls = []
    manager = _manager()
    _register(
        manager,
        "primary",
        1,
        [
            AIResponse(tool_calls=(AIToolCall(name="attack", call_id="call-1"),)),
            AIResponse(text="done"),
        ],
        calls,
        priority=2,
    )
    _register(manager, "fallback", 1, [AIResponse(text="wrong")], calls)

    chat = manager.start_chat(system_prompt="system", tools=[{"name": "attack"}])
    first = chat.send("fight")
    final = chat.send_tool_results([AIToolResult(name="attack", result={"ok": True}, call_id="call-1")])

    assert first.tool_calls[0].name == "attack"
    assert final.text == "done"
    assert calls == ["primary"]


def test_managed_chat_reroutes_after_scenario_reset():
    calls = []
    manager = _manager()
    _register(manager, "primary", 1, [AIResponse(text="first")], calls, priority=2)
    _register(manager, "fallback", 1, [AIResponse(text="second")], calls)
    chat = manager.start_chat(system_prompt="system", tools=[])

    assert chat.send("one").text == "first"
    chat.reset_scenario()
    manager.set_enabled("primary", False)
    assert chat.send("two").text == "second"
    assert calls == ["primary", "fallback"]
