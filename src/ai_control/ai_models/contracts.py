"""Stable contracts shared by Scenario Engine, Chat and AI model adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AIToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""


@dataclass(frozen=True)
class AIToolResult:
    name: str
    result: dict[str, Any]
    call_id: str = ""


@dataclass(frozen=True)
class AIUsage:
    """Provider-reported token usage for one model request."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class AIResponse:
    text: str = ""
    tool_calls: tuple[AIToolCall, ...] = ()
    usage: AIUsage | None = None


class AIChatSession(ABC):
    """One provider-specific conversation exposed through a common API."""

    @property
    @abstractmethod
    def history(self) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    def send(self, content: Any) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    def send_tool_results(self, results: list[AIToolResult]) -> AIResponse:
        raise NotImplementedError

    def reset_scenario(self) -> None:
        """Discard dynamic scenario context while preserving provider session defaults."""
        return None


class AIModelAdapter(ABC):
    """Provider adapter created by :class:`AIModelFactory`."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def validate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_chat(
        self,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> AIChatSession:
        raise NotImplementedError
