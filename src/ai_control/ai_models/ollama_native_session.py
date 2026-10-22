"""Native Ollama chat session using the ``/api/chat`` endpoint."""

from __future__ import annotations

import base64
import io
import json
from typing import Any, Callable
from uuid import uuid4

from src.ai_control.ai_models.contracts import (
    AIChatSession,
    AIResponse,
    AIToolCall,
    AIToolResult,
    AIUsage,
)


JsonRequest = Callable[[str, dict[str, Any] | None], dict[str, Any]]


class OllamaNativeChatSession(AIChatSession):
    """Translate the shared chat contract to Ollama's native message format."""

    def __init__(
        self,
        request_json: JsonRequest,
        model_name: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        *,
        max_tokens: int | None = None,
        keep_alive: str | int | None = "30m",
        history: list[Any] | None = None,
    ) -> None:
        self._request_json = request_json
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._keep_alive = keep_alive
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
        self._static_history: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]
        self._history: list[dict[str, Any]] = list(self._static_history)
        if history:
            self._history.extend(history)

    @property
    def history(self) -> list[Any]:
        return list(self._history)

    @staticmethod
    def _user_message(content: Any) -> dict[str, Any]:
        if not isinstance(content, list):
            return {"role": "user", "content": str(content or "")}

        text_parts: list[str] = []
        images: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif hasattr(item, "save"):
                image_bytes = io.BytesIO()
                item.save(image_bytes, format="PNG")
                images.append(base64.b64encode(image_bytes.getvalue()).decode("ascii"))
        message: dict[str, Any] = {"role": "user", "content": "\n".join(text_parts)}
        if images:
            message["images"] = images
        return message

    def _complete(self) -> AIResponse:
        request: dict[str, Any] = {
            "model": self._model_name,
            "messages": self._history,
            "stream": False,
            "think": False,
        }
        if self._tools:
            request["tools"] = self._tools
        if self._keep_alive is not None:
            request["keep_alive"] = self._keep_alive
        if self._max_tokens is not None:
            request["options"] = {"num_predict": self._max_tokens}

        payload = self._request_json("/api/chat", request)
        raw_message = dict(payload.get("message") or {})
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": str(raw_message.get("content") or ""),
        }
        raw_calls = list(raw_message.get("tool_calls") or [])
        if raw_calls:
            assistant_message["tool_calls"] = raw_calls
        self._history.append(assistant_message)

        calls: list[AIToolCall] = []
        for raw_call in raw_calls:
            function = dict(raw_call.get("function") or {})
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            name = str(function.get("name") or "").strip()
            if name:
                calls.append(
                    AIToolCall(
                        name=name,
                        arguments=arguments,
                        call_id=str(raw_call.get("id") or f"ollama-{uuid4().hex}"),
                    )
                )

        input_tokens = self._optional_int(payload.get("prompt_eval_count"))
        output_tokens = self._optional_int(payload.get("eval_count"))
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        usage = None
        if input_tokens is not None or output_tokens is not None:
            usage = AIUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )
        return AIResponse(
            text=assistant_message["content"],
            tool_calls=tuple(calls),
            usage=usage,
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def send(self, content: Any) -> AIResponse:
        self._history.append(self._user_message(content))
        return self._complete()

    def send_tool_results(self, results: list[AIToolResult]) -> AIResponse:
        for result in results:
            self._history.append(
                {
                    "role": "tool",
                    "tool_name": result.name,
                    "content": json.dumps(result.result, ensure_ascii=False, default=str),
                }
            )
        return self._complete()

    def reset_scenario(self) -> None:
        self._history = list(self._static_history)
