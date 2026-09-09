"""Gemini implementation of the provider-neutral AI model contracts."""

from __future__ import annotations

from typing import Any

from src.ai_control.ai_models.contracts import (
    AIChatSession,
    AIModelAdapter,
    AIResponse,
    AIToolCall,
    AIToolResult,
)
from src.ai_control.gemini_tool_bridge import (
    build_gemini_tool_declarations,
    extract_function_calls,
    response_text,
)


class GeminiChatSession(AIChatSession):
    def __init__(self, raw_chat: Any, sdk_module: Any) -> None:
        self._raw_chat = raw_chat
        self._sdk = sdk_module

    @property
    def history(self) -> list[Any]:
        try:
            return list(self._raw_chat.history)
        except Exception:
            return []

    @staticmethod
    def _normalize_response(response: Any) -> AIResponse:
        calls = tuple(
            AIToolCall(name=call["name"], arguments=dict(call.get("arguments") or {}))
            for call in extract_function_calls(response)
        )
        return AIResponse(text=response_text(response), tool_calls=calls)

    def send(self, content: Any) -> AIResponse:
        return self._normalize_response(self._raw_chat.send_message(content))

    def send_tool_results(self, results: list[AIToolResult]) -> AIResponse:
        parts = []
        for item in results:
            function_response = self._sdk.protos.FunctionResponse(name=item.name, response=item.result)
            parts.append(self._sdk.protos.Part(function_response=function_response))
        return self._normalize_response(self._raw_chat.send_message(parts))


class GeminiModelAdapter(AIModelAdapter):
    def __init__(self, *, model_name: str, api_key: str, sdk_module: Any) -> None:
        clean_model = str(model_name or "").strip()
        clean_key = str(api_key or "").strip()
        if not clean_model:
            raise ValueError("Tên Gemini model không được để trống")
        if not clean_key:
            raise ValueError("Gemini API key không được để trống")
        if sdk_module is None:
            raise RuntimeError("Gemini SDK chưa được cài")
        self._model_name = clean_model
        self._api_key = clean_key
        self._sdk = sdk_module

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def validate(self) -> None:
        self._sdk.configure(api_key=self._api_key)
        if hasattr(self._sdk, "get_model"):
            try:
                self._sdk.get_model(f"models/{self._model_name}")
            except Exception as exc:
                raise RuntimeError(f"Model không dùng được: {exc}") from exc

    def start_chat(
        self,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> AIChatSession:
        prompt = str(system_prompt or "").strip()
        if not prompt:
            raise ValueError("Mọi AI model bắt buộc phải nhận system prompt dùng chung")
        declarations = build_gemini_tool_declarations(self._sdk, tools)
        tool_payload = [{"function_declarations": declarations}] if declarations else None
        model = self._sdk.GenerativeModel(
            self._model_name,
            tools=tool_payload,
            system_instruction=prompt,
        )
        return GeminiChatSession(model.start_chat(history=list(history or [])), self._sdk)

