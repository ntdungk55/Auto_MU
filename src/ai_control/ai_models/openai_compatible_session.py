"""Shared chat-session translation for OpenAI-compatible providers."""

from __future__ import annotations

import base64
import io
import json
from typing import Any

from src.ai_control.ai_models.contracts import (
    AIChatSession,
    AIResponse,
    AIToolCall,
    AIToolResult,
    AIUsage,
)


class OpenAICompatibleChatSession(AIChatSession):
    """Translate shared chat contracts to the OpenAI Chat Completions API."""

    def __init__(
        self,
        client: Any,
        model_name: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        *,
        max_tokens: int | None = None,
        completion_options: dict[str, Any] | None = None,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._completion_options = dict(completion_options or {})
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
    def _response(response: Any) -> AIResponse:
        message = response.choices[0].message
        calls = []
        for call in list(getattr(message, "tool_calls", None) or []):
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            calls.append(AIToolCall(name=call.function.name, arguments=arguments, call_id=call.id))
        raw_usage = getattr(response, "usage", None)
        usage = None
        if raw_usage is not None:
            usage = AIUsage(
                input_tokens=getattr(raw_usage, "prompt_tokens", None),
                output_tokens=getattr(raw_usage, "completion_tokens", None),
                total_tokens=getattr(raw_usage, "total_tokens", None),
            )
        return AIResponse(
            text=str(getattr(message, "content", "") or ""),
            tool_calls=tuple(calls),
            usage=usage,
        )

    def _complete(self) -> AIResponse:
        request: dict[str, Any] = {
            "model": self._model_name,
            "messages": self._history,
            "tools": self._tools or None,
            **self._completion_options,
        }
        if self._max_tokens is not None:
            request["max_tokens"] = self._max_tokens
        response = self._client.chat.completions.create(**request)
        message = response.choices[0].message
        self._history.append(message.model_dump(exclude_none=True))
        return self._response(response)

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
        self._history = list(self._static_history)
