"""Bridge the sample event controller to the shared AIManager."""

from __future__ import annotations

from datetime import datetime, timezone

from src.ai_control.ai_manager import AIManager

from ..application.ai_agent import AIAgent, AIRequest, AIResponse


class ManagedAIAgent(AIAgent):
    """Route event prompts through every provider registered in AIManager."""

    def __init__(self, manager: AIManager) -> None:
        self._manager = manager

    def respond(self, request: AIRequest) -> AIResponse:
        chat = self._manager.start_chat(system_prompt=request.system_prompt, tools=[])
        response = chat.send(request.prompt)
        active_model_id = str(getattr(chat, "active_model_id", "") or "")
        statuses = {str(item["id"]): item for item in self._manager.model_status()}
        model_name = str(statuses.get(active_model_id, {}).get("model_name", active_model_id))
        return AIResponse(
            text=response.text,
            model_name=model_name,
            created_at=datetime.now(timezone.utc),
        )
