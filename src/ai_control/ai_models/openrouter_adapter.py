"""OpenRouter implementation of the provider-neutral AI contracts."""

from __future__ import annotations

from typing import Any

from src.ai_control.ai_models.contracts import AIChatSession, AIModelAdapter
from src.ai_control.ai_models.openai_compatible_session import OpenAICompatibleChatSession

OPENROUTER_MAX_TOKENS = 4996


OpenRouterChatSession = OpenAICompatibleChatSession


class OpenRouterModelAdapter(AIModelAdapter):
    """Create an OpenRouter chat session through the official OpenAI Python SDK."""

    def __init__(self, *, model_name: str, api_key: str, client_class: Any | None = None, **_: Any) -> None:
        self._model_name = str(model_name or "").strip()
        self._api_key = str(api_key or "").strip()
        self._client_class = client_class
        if not self._model_name:
            raise ValueError("Tên OpenRouter model không được để trống")
        if not self._api_key:
            raise ValueError("OpenRouter API key không được để trống")

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _client(self) -> Any:
        if self._client_class is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Chưa cài OpenAI SDK. Hãy cài dependency 'openai'.") from exc
            self._client_class = OpenAI
        return self._client_class(base_url="https://openrouter.ai/api/v1", api_key=self._api_key)

    def validate(self) -> None:
        self._client()

    def start_chat(self, *, system_prompt: str, tools: list[dict[str, Any]], history: list[Any] | None = None) -> AIChatSession:
        prompt = str(system_prompt or "").strip()
        if not prompt:
            raise ValueError("Mọi AI model bắt buộc phải nhận system prompt dùng chung")
        session = OpenRouterChatSession(
            self._client(),
            self._model_name,
            prompt,
            tools,
            max_tokens=OPENROUTER_MAX_TOKENS,
            completion_options={"parallel_tool_calls": False},
        )
        if history:
            session._history.extend(history)
        return session
