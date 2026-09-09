"""AI agent construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AIAgentFactory:
    """Create interchangeable AI agents from registered provider builders."""

    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., Any]] = {}

    def register(self, provider: str, builder: Callable[..., Any]) -> None:
        """Register one provider builder."""
        self._builders[provider.casefold()] = builder

    def create(self, provider: str, **kwargs: Any) -> Any:
        """Create an agent for a registered provider."""
        key = provider.casefold()
        if key not in self._builders:
            raise ValueError(f"Unsupported AI provider: {provider}")
        return self._builders[key](**kwargs)
