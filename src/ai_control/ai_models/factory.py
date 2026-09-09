"""Registry-based factory for interchangeable AI model adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.ai_control.ai_models.contracts import AIModelAdapter


AdapterConstructor = Callable[..., AIModelAdapter]


class AIModelFactory:
    """Create adapters without coupling callers to a provider SDK."""

    def __init__(self) -> None:
        self._registry: dict[str, AdapterConstructor] = {}

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        return str(provider or "").strip().casefold()

    def register(
        self,
        provider: str,
        constructor: AdapterConstructor,
        *,
        replace: bool = False,
    ) -> None:
        name = self._normalize_provider(provider)
        if not name:
            raise ValueError("Tên AI provider không được để trống")
        if not callable(constructor):
            raise TypeError("Adapter constructor phải callable")
        if name in self._registry and not replace:
            raise ValueError(f"AI provider đã được đăng ký: {name}")
        self._registry[name] = constructor

    def create(self, provider: str, **config: Any) -> AIModelAdapter:
        name = self._normalize_provider(provider)
        constructor = self._registry.get(name)
        if constructor is None:
            available = ", ".join(self.available_providers()) or "không có"
            raise ValueError(f"AI provider không được hỗ trợ: {provider}. Đang có: {available}")
        adapter = constructor(**config)
        if not isinstance(adapter, AIModelAdapter):
            raise TypeError(f"Factory của provider '{name}' không trả về AIModelAdapter")
        return adapter

    def available_providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._registry))


def create_default_ai_model_factory() -> AIModelFactory:
    """Return the app factory with every currently installed adapter."""
    from src.ai_control.ai_models.gemini_adapter import GeminiModelAdapter

    factory = AIModelFactory()
    factory.register("gemini", GeminiModelAdapter)
    return factory

