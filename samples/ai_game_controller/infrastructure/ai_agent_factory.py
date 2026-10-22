"""AI agent construction."""

from __future__ import annotations

from collections.abc import Callable

from ..application.ai_agent import AIAgent


class AIAgentFactory:
    """Create interchangeable AI agents from registered provider builders."""

    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., AIAgent]] = {}

    def register(self, provider: str, builder: Callable[..., AIAgent]) -> None:
        """Register one provider builder."""
        self._builders[provider.casefold()] = builder

    def create(self, provider: str, **kwargs: object) -> AIAgent:
        """Create an agent for a registered provider."""
        key = provider.casefold()
        if key not in self._builders:
            raise ValueError(f"Unsupported AI provider: {provider}")
        return self._builders[key](**kwargs)
