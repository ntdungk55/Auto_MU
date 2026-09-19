"""Small, provider-neutral manager for routing requests across free AI models."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

from src.ai_control.ai_models.contracts import AIResponse
from src.ai_control.ai_models.factory import AIModelFactory, create_default_ai_model_factory


class AIManager:
    """Select, call and fail over between registered AI model deployments.

    Version one intentionally keeps registry, routing, quota, health and retry in
    one application-facing class. Provider-specific HTTP and response handling
    remain in ``AIModelAdapter`` implementations created by ``AIModelFactory``.
    """

    _QUOTA_ERROR_MARKERS = (
        "quota exceeded",
        "quota_exceeded",
        "resource exhausted",
        "resource_exhausted",
        "daily quota",
        "monthly quota",
        "billing quota",
    )

    def __init__(
        self,
        factory: AIModelFactory | None = None,
        *,
        max_retries_per_model: int = 1,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_retries_per_model < 0:
            raise ValueError("Số lần retry không được âm")
        if cooldown_seconds < 0:
            raise ValueError("Thời gian cooldown không được âm")
        self._factory = factory or create_default_ai_model_factory()
        self._max_retries = int(max_retries_per_model)
        self._cooldown_seconds = float(cooldown_seconds)
        self._clock = clock
        self._sleep = sleep
        self._models: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register_model(
        self,
        model_id: str,
        *,
        provider: str,
        model_name: str,
        adapter_config: dict[str, Any] | None = None,
        supports_tools: bool = True,
        intelligence_level: int = 1,
        context_window: int = 8_192,
        token_quota: int | None = None,
        quota_window_seconds: float | None = None,
        priority: int = 0,
        enabled: bool = True,
    ) -> None:
        """Add one independently tracked model/provider/credential deployment."""
        clean_id = str(model_id or "").strip()
        clean_provider = str(provider or "").strip().casefold()
        clean_model = str(model_name or "").strip()
        if not clean_id or not clean_provider or not clean_model:
            raise ValueError("model_id, provider và model_name không được để trống")
        if intelligence_level not in (1, 2, 3):
            raise ValueError("intelligence_level phải là 1, 2 hoặc 3")
        if context_window <= 0:
            raise ValueError("context_window phải lớn hơn 0")
        if token_quota is not None and token_quota < 0:
            raise ValueError("token_quota không được âm")
        if quota_window_seconds is not None and quota_window_seconds <= 0:
            raise ValueError("quota_window_seconds phải lớn hơn 0")

        now = self._clock()
        with self._lock:
            if clean_id in self._models:
                raise ValueError(f"AI model deployment đã tồn tại: {clean_id}")
            self._models[clean_id] = {
                "id": clean_id,
                "provider": clean_provider,
                "model_name": clean_model,
                "adapter_config": dict(adapter_config or {}),
                "supports_tools": bool(supports_tools),
                "intelligence_level": int(intelligence_level),
                "context_window": int(context_window),
                "token_quota": token_quota,
                "remaining_tokens": token_quota,
                "quota_window_seconds": quota_window_seconds,
                "quota_reset_at": now + quota_window_seconds if quota_window_seconds else None,
                "priority": int(priority),
                "enabled": bool(enabled),
                "cooldown_until": 0.0,
                "reserved_tokens": 0,
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "used_tokens": 0,
                "average_latency_ms": 0.0,
                "last_error": None,
            }

    def execute(
        self,
        content: Any,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        history: list[Any] | None = None,
        difficulty: int | None = None,
        max_output_tokens: int = 1_024,
    ) -> AIResponse:
        """Route one request and return the first successful provider response."""
        prompt = str(system_prompt or "").strip()
        if not prompt:
            raise ValueError("system_prompt không được để trống")
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens phải lớn hơn 0")
        requested_tools = list(tools or [])
        required_level = self._assess_difficulty(content, requested_tools, difficulty)
        estimated_tokens = self._estimate_tokens(
            content,
            prompt,
            requested_tools,
            history or [],
            max_output_tokens,
        )
        candidate_ids = self._rank_candidates(
            required_level=required_level,
            estimated_tokens=estimated_tokens,
            requires_tools=bool(requested_tools),
        )
        if not candidate_ids:
            raise RuntimeError("Không có AI model đáp ứng capability, quota, context và health")

        last_error: Exception | None = None
        for model_id in candidate_ids:
            if not self._reserve(model_id, estimated_tokens):
                continue
            try:
                for attempt in range(self._max_retries + 1):
                    started = self._clock()
                    try:
                        response = self._call_model(
                            model_id,
                            content=content,
                            system_prompt=prompt,
                            tools=requested_tools,
                            history=history,
                        )
                    except Exception as exc:
                        last_error = exc
                        error_kind = self._classify_error(exc)
                        if error_kind == "transient" and attempt < self._max_retries:
                            self._sleep(min(2**attempt, 4))
                            continue
                        self._record_failure(model_id, exc, error_kind)
                        if error_kind == "fatal_request":
                            raise
                        break
                    else:
                        latency_ms = max(0.0, (self._clock() - started) * 1_000)
                        actual_tokens = self._response_tokens(response) or estimated_tokens
                        self._record_success(model_id, actual_tokens, latency_ms)
                        return response
            finally:
                self._release_reservation(model_id, estimated_tokens)

        if last_error is not None:
            raise RuntimeError(f"Tất cả AI model đều thất bại: {last_error}") from last_error
        raise RuntimeError("Không còn AI model đủ quota để thực hiện request")

    def model_status(self) -> tuple[dict[str, Any], ...]:
        """Return routing state without exposing adapter config or credentials."""
        now = self._clock()
        with self._lock:
            statuses = []
            for model in self._models.values():
                self._reset_quota_if_due(model, now)
                statuses.append(
                    {
                        "id": model["id"],
                        "provider": model["provider"],
                        "model_name": model["model_name"],
                        "enabled": model["enabled"],
                        "healthy": model["cooldown_until"] <= now,
                        "cooldown_remaining_seconds": max(0.0, model["cooldown_until"] - now),
                        "remaining_tokens": model["remaining_tokens"],
                        "reserved_tokens": model["reserved_tokens"],
                        "requests": model["requests"],
                        "successes": model["successes"],
                        "failures": model["failures"],
                        "used_tokens": model["used_tokens"],
                        "average_latency_ms": model["average_latency_ms"],
                        "last_error": model["last_error"],
                    }
                )
            return tuple(statuses)

    def set_enabled(self, model_id: str, enabled: bool) -> None:
        with self._lock:
            self._model(model_id)["enabled"] = bool(enabled)

    def reset_quota(self, model_id: str) -> None:
        """Reset a deployment after its provider quota window has renewed."""
        with self._lock:
            model = self._model(model_id)
            model["remaining_tokens"] = model["token_quota"]
            window = model["quota_window_seconds"]
            model["quota_reset_at"] = self._clock() + window if window else None

    def _call_model(
        self,
        model_id: str,
        *,
        content: Any,
        system_prompt: str,
        tools: list[dict[str, Any]],
        history: list[Any] | None,
    ) -> AIResponse:
        with self._lock:
            model = self._model(model_id)
            provider = model["provider"]
            model_name = model["model_name"]
            config = dict(model["adapter_config"])
        config.pop("model_name", None)
        adapter = self._factory.create(provider, model_name=model_name, **config)
        adapter.validate()
        chat = adapter.start_chat(system_prompt=system_prompt, tools=tools, history=history)
        response = chat.send(content)
        if not isinstance(response, AIResponse):
            raise TypeError("AI provider không trả về AIResponse")
        return response

    def _rank_candidates(
        self,
        *,
        required_level: int,
        estimated_tokens: int,
        requires_tools: bool,
    ) -> list[str]:
        now = self._clock()
        ranked: list[tuple[float, str]] = []
        with self._lock:
            for model in self._models.values():
                self._reset_quota_if_due(model, now)
                if not model["enabled"] or model["cooldown_until"] > now:
                    continue
                if requires_tools and not model["supports_tools"]:
                    continue
                if estimated_tokens > model["context_window"]:
                    continue
                remaining = model["remaining_tokens"]
                if remaining is not None and remaining - model["reserved_tokens"] < estimated_tokens:
                    continue
                ranked.append((self._score(model, required_level), model["id"]))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [model_id for _, model_id in ranked]

    @staticmethod
    def _score(model: dict[str, Any], required_level: int) -> float:
        level_gap = model["intelligence_level"] - required_level
        difficulty_fit = 60.0 - abs(level_gap) * 25.0
        if level_gap < 0:
            difficulty_fit -= abs(level_gap) * 25.0
        quota = model["token_quota"]
        remaining = model["remaining_tokens"]
        quota_headroom = 20.0 if quota is None else 20.0 * (remaining or 0) / max(quota, 1)
        attempts = model["successes"] + model["failures"]
        reliability = 10.0 if attempts == 0 else 10.0 * model["successes"] / attempts
        latency_penalty = min(model["average_latency_ms"] / 1_000.0, 10.0)
        return difficulty_fit + quota_headroom + reliability + model["priority"] * 10 - latency_penalty

    @staticmethod
    def _assess_difficulty(content: Any, tools: list[dict[str, Any]], explicit: int | None) -> int:
        if explicit is not None:
            if explicit not in (1, 2, 3):
                raise ValueError("difficulty phải là 1, 2 hoặc 3")
            return explicit
        size = len(str(content or ""))
        if len(tools) >= 12 or size >= 4_000:
            return 3
        if len(tools) >= 5 or size >= 1_000:
            return 2
        return 1

    @staticmethod
    def _estimate_tokens(
        content: Any,
        system_prompt: str,
        tools: list[dict[str, Any]],
        history: list[Any],
        max_output_tokens: int,
    ) -> int:
        serialized = "\n".join(
            (
                system_prompt,
                str(content or ""),
                json.dumps(tools, ensure_ascii=False, default=str),
                json.dumps(history, ensure_ascii=False, default=str),
            )
        )
        input_estimate = max(1, (len(serialized) + 3) // 4)
        return input_estimate + max_output_tokens

    def _reserve(self, model_id: str, estimated_tokens: int) -> bool:
        with self._lock:
            model = self._model(model_id)
            remaining = model["remaining_tokens"]
            if remaining is not None and remaining - model["reserved_tokens"] < estimated_tokens:
                return False
            model["reserved_tokens"] += estimated_tokens
            return True

    def _release_reservation(self, model_id: str, estimated_tokens: int) -> None:
        with self._lock:
            model = self._model(model_id)
            model["reserved_tokens"] = max(0, model["reserved_tokens"] - estimated_tokens)

    def _record_success(self, model_id: str, used_tokens: int, latency_ms: float) -> None:
        with self._lock:
            model = self._model(model_id)
            model["requests"] += 1
            model["successes"] += 1
            model["used_tokens"] += used_tokens
            if model["remaining_tokens"] is not None:
                model["remaining_tokens"] = max(0, model["remaining_tokens"] - used_tokens)
            count = model["successes"]
            old_average = model["average_latency_ms"]
            model["average_latency_ms"] = old_average + (latency_ms - old_average) / count
            model["last_error"] = None

    def _record_failure(self, model_id: str, exc: Exception, error_kind: str) -> None:
        now = self._clock()
        with self._lock:
            model = self._model(model_id)
            model["requests"] += 1
            model["failures"] += 1
            model["last_error"] = str(exc)
            if error_kind == "auth":
                model["enabled"] = False
            elif error_kind == "quota":
                if model["remaining_tokens"] is not None:
                    model["remaining_tokens"] = 0
                reset_at = model["quota_reset_at"]
                model["cooldown_until"] = reset_at or now + self._cooldown_seconds
            elif error_kind in ("rate_limit", "transient"):
                retry_after = self._retry_after(exc)
                model["cooldown_until"] = now + (retry_after or self._cooldown_seconds)

    @classmethod
    def _classify_error(cls, exc: Exception) -> str:
        status = getattr(exc, "status_code", None)
        if status is None:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
        message = str(exc).casefold()
        if status in (401, 403):
            return "auth"
        if status == 429:
            return "quota" if any(marker in message for marker in cls._QUOTA_ERROR_MARKERS) else "rate_limit"
        if status is not None and 400 <= status < 500:
            return "fatal_request"
        if status is not None and status >= 500:
            return "transient"
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return "transient"
        return "fatal_request"

    @staticmethod
    def _retry_after(exc: Exception) -> float | None:
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None) or getattr(exc, "headers", None) or {}
        value = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return max(0.0, float(value)) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _response_tokens(response: AIResponse) -> int | None:
        if response.usage is None:
            return None
        if response.usage.total_tokens is not None:
            return max(0, response.usage.total_tokens)
        values = (response.usage.input_tokens, response.usage.output_tokens)
        if all(value is None for value in values):
            return None
        return sum(max(0, value or 0) for value in values)

    def _reset_quota_if_due(self, model: dict[str, Any], now: float) -> None:
        reset_at = model["quota_reset_at"]
        window = model["quota_window_seconds"]
        if reset_at is None or window is None or now < reset_at:
            return
        model["remaining_tokens"] = model["token_quota"]
        model["quota_reset_at"] = now + window
        model["cooldown_until"] = min(model["cooldown_until"], now)

    def _model(self, model_id: str) -> dict[str, Any]:
        clean_id = str(model_id or "").strip()
        try:
            return self._models[clean_id]
        except KeyError as exc:
            raise KeyError(f"Không tìm thấy AI model deployment: {clean_id}") from exc
