"""OpenRouter implementation of the sample AI-agent contract."""

from __future__ import annotations

from datetime import datetime, timezone

from ..application.ai_agent import AIAgent, AIRequest, AIResponse


class OpenRouterAgent(AIAgent):
    """Generate event responses using OpenRouter's OpenAI-compatible API."""

    def __init__(self, api_key: str, model_name: str) -> None:
        self._api_key = api_key.strip()
        self._model_name = model_name.strip()

    def respond(self, request: AIRequest) -> AIResponse:
        if not self._api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        if not self._model_name:
            raise RuntimeError("OpenRouter model is not configured")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("openai is not installed") from error
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
        )
        return AIResponse(
            text=str(response.choices[0].message.content or ""),
            model_name=self._model_name,
            created_at=datetime.now(timezone.utc),
        )
