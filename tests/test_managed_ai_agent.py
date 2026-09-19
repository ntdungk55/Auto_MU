from __future__ import annotations

from datetime import timezone

from samples.ai_game_controller.application.ai_agent import AIRequest
from samples.ai_game_controller.infrastructure.managed_ai_agent import ManagedAIAgent
from src.ai_control.ai_models.contracts import AIResponse


class _Chat:
    active_model_id = "gemini:flash"

    def send(self, prompt):
        assert prompt == "event prompt"
        return AIResponse(text="handled")


class _Manager:
    def start_chat(self, *, system_prompt, tools):
        assert system_prompt == "system"
        assert tools == []
        return _Chat()

    def model_status(self):
        return ({"id": "gemini:flash", "model_name": "flash"},)


def test_managed_ai_agent_routes_event_request_through_ai_manager():
    agent = ManagedAIAgent(_Manager())

    response = agent.respond(AIRequest(system_prompt="system", prompt="event prompt", target_id="game-1"))

    assert response.text == "handled"
    assert response.model_name == "flash"
    assert response.created_at.tzinfo == timezone.utc
