"""Application contract for AI requests and responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AIRequest:
    """One provider-independent request derived from a game event."""

    system_prompt: str
    prompt: str
    target_id: str


@dataclass(frozen=True, slots=True)
class AIResponse:
    """One provider-independent text response from an AI agent."""

    text: str
    model_name: str
    created_at: datetime
    error: str | None = None


class AIAgent(Protocol):
    """Generate an AI response for one event-driven request."""

    def respond(self, request: AIRequest) -> AIResponse:
        """Send one request to the configured provider."""
