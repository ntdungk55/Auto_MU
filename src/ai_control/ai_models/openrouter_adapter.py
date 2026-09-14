"""OpenRouter implementation of the provider-neutral AI contracts."""

from __future__ import annotations

import base64
import io
import json
from typing import Any

from src.ai_control.ai_models.contracts import (
    AIChatSession,
    AIModelAdapter,
    AIResponse,
    AIToolCall,
    AIToolResult,
)

OPENROUTER_MAX_TOKENS = 4996


class OpenRouterChatSession(AIChatSession):
    """Translate the shared chat contract to OpenRouter's OpenAI-compatible API."""

    def __init__(self, client: Any, model_name: str, system_prompt: str, tools: list[dict[str, Any]]) -> None:
        self._client = client
        self._model_name = model_name
        self._tools = [
            {
                "type": "function",
                "function": {
                    "name": str(tool["name"]),
                    "description": str(tool.get("description") or ""),
                    "parameters": dict(tool.get("input_schema") or {"type": "object"}),
                },
            }
            for tool in tools
            if str(tool.get("name") or "").strip()
        ]
        self._static_history: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        self._history: list[dict[str, Any]] = list(self._static_history)

    @property
    def history(self) -> list[Any]:
        return list(self._history)

    @staticmethod
    def _content(content: Any) -> Any:
        if not isinstance(content, list):
            return str(content or "")
        parts: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, str):
                parts.append({"type": "text", "text": item})
            elif hasattr(item, "save"):
                image_bytes = io.BytesIO()
                item.save(image_bytes, format="PNG")
                encoded = base64.b64encode(image_bytes.getvalue()).decode("ascii")
                parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
        return parts or [{"type": "text", "text": ""}]

    @staticmethod
    def _response(message: Any) -> AIResponse:
        calls = []
        for call in list(getattr(message, "tool_calls", None) or []):
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            calls.append(AIToolCall(name=call.function.name, arguments=arguments, call_id=call.id))
        return AIResponse(text=str(getattr(message, "content", "") or ""), tool_calls=tuple(calls))

    def _complete(self) -> AIResponse:
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=self._history,
            tools=self._tools or None,
            parallel_tool_calls=False,
            max_tokens=OPENROUTER_MAX_TOKENS,
        )
        message = response.choices[0].message
        self._history.append(message.model_dump(exclude_none=True))
        return self._response(message)

    def send(self, content: Any) -> AIResponse:
        self._history.append({"role": "user", "content": self._content(content)})
        return self._complete()

    def send_tool_results(self, results: list[AIToolResult]) -> AIResponse:
        for result in results:
            self._history.append(
                {
                    "role": "tool",
                    "tool_call_id": result.call_id,
                    "content": json.dumps(result.result, ensure_ascii=False, default=str),
                }
            )
        return self._complete()

    def reset_scenario(self) -> None:
        """Keep only immutable system context after a scenario reaches a terminal state."""
        self._history = list(self._static_history)


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
        session = OpenRouterChatSession(self._client(), self._model_name, prompt, tools)
        if history:
            session._history.extend(history)
        return session
