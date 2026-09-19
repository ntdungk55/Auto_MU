"""Ollama provider exposed through its OpenAI-compatible API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from src.ai_control.ai_models.contracts import AIChatSession, AIModelAdapter
from src.ai_control.ai_models.openai_compatible_session import OpenAICompatibleChatSession


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
OLLAMA_PLACEHOLDER_API_KEY = "ollama"


def _environment_value(name: str) -> str:
    """Read a process variable, then the persistent Windows user environment."""
    value = str(os.environ.get(name, "") or "").strip()
    if value or os.name != "nt":
        return value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            stored, _ = winreg.QueryValueEx(key, name)
        return str(stored or "").strip()
    except (FileNotFoundError, OSError):
        return ""


class OllamaModelAdapter(AIModelAdapter):
    """Use the official OpenAI SDK with a local or tunneled Ollama server."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str | None = None,
        cf_access_client_id: str | None = None,
        cf_access_client_secret: str | None = None,
        default_headers: Mapping[str, str] | None = None,
        api_key: str = OLLAMA_PLACEHOLDER_API_KEY,
        max_tokens: int | None = None,
        timeout: float = 600.0,
        max_retries: int = 1,
        client_class: Any | None = None,
        **_: Any,
    ) -> None:
        self._model_name = str(model_name or "").strip()
        self._base_url = self._normalize_base_url(base_url or _environment_value("OLLAMA_BASE_URL"))
        self._api_key = str(api_key or OLLAMA_PLACEHOLDER_API_KEY).strip()
        self._max_tokens = int(max_tokens) if max_tokens is not None else None
        self._timeout = float(timeout)
        self._max_retries = int(max_retries)
        self._client_class = client_class
        self._client_instance: Any | None = None

        client_id = str(
            cf_access_client_id
            if cf_access_client_id is not None
            else _environment_value("CF_ACCESS_CLIENT_ID")
        ).strip()
        client_secret = str(
            cf_access_client_secret
            if cf_access_client_secret is not None
            else _environment_value("CF_ACCESS_CLIENT_SECRET")
        ).strip()
        if bool(client_id) != bool(client_secret):
            raise ValueError("Cloudflare Access yêu cầu đủ Client ID và Client Secret")
        self._default_headers = dict(default_headers or {})
        if client_id:
            self._default_headers.update(
                {
                    "CF-Access-Client-Id": client_id,
                    "CF-Access-Client-Secret": client_secret,
                }
            )

        if not self._model_name:
            raise ValueError("Tên Ollama model không được để trống")
        if self._max_tokens is not None and self._max_tokens <= 0:
            raise ValueError("max_tokens phải lớn hơn 0")
        if self._timeout <= 0:
            raise ValueError("timeout phải lớn hơn 0")
        if self._max_retries < 0:
            raise ValueError("max_retries không được âm")

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        url = str(value or DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL phải bắt đầu bằng http:// hoặc https://")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        return url

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def _client(self) -> Any:
        if self._client_instance is not None:
            return self._client_instance
        client_class = self._client_class
        if client_class is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Chưa cài OpenAI SDK. Hãy cài dependency 'openai'.") from exc
            client_class = OpenAI
        self._client_instance = client_class(
            base_url=self._base_url,
            api_key=self._api_key,
            default_headers=self._default_headers or None,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )
        return self._client_instance

    def validate(self) -> None:
        available = {
            str(getattr(model, "id", "") or "").strip()
            for model in self._client().models.list().data
        }
        if self._model_name not in available:
            choices = ", ".join(sorted(item for item in available if item)) or "không có"
            raise ValueError(f"Ollama model không tồn tại: {self._model_name}. Đang có: {choices}")

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
        session = OpenAICompatibleChatSession(
            self._client(),
            self._model_name,
            prompt,
            tools,
            max_tokens=self._max_tokens,
            completion_options={"extra_body": {"think": False}},
        )
        if history:
            session._history.extend(history)
        return session
