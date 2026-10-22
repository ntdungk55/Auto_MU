"""Gemini implementation of the sample AI-agent contract."""

from __future__ import annotations

from datetime import datetime, timezone

from ..application.ai_agent import AIAgent, AIRequest, AIResponse


class GeminiAgent(AIAgent):
    """Send event prompts to Gemini without exposing SDK types to application code."""

    def __init__(self, api_key: str, model_name: str) -> None:
        self._api_key = api_key.strip()
        self._model_name = model_name.strip()

    def respond(self, request: AIRequest) -> AIResponse:
        """Generate one text response through the configured Gemini model."""
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        if not self._model_name:
            raise RuntimeError("Gemini model is not configured")
        try:
            import google.generativeai as genai
        except ImportError as error:
            raise RuntimeError("google-generativeai is not installed") from error
        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model_name, system_instruction=request.system_prompt)
        response = model.generate_content(request.prompt)
        return AIResponse(
            text=str(getattr(response, "text", "") or ""),
            model_name=self._model_name,
            created_at=datetime.now(timezone.utc),
        )
