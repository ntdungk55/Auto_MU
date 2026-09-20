"""Ollama provider using the native HTTP API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from src.ai_control.ai_models.contracts import AIChatSession, AIModelAdapter
from src.ai_control.ai_models.ollama_native_session import OllamaNativeChatSession


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"


class OllamaHTTPError(RuntimeError):
    """HTTP failure carrying metadata used by AIManager health handling."""

    def __init__(self, status_code: int, message: str, headers: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers or {}


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
    """Call a local or tunneled Ollama server through ``/api/*`` endpoints."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str | None = None,
        cf_access_client_id: str | None = None,
        cf_access_client_secret: str | None = None,
        default_headers: Mapping[str, str] | None = None,
        max_tokens: int | None = None,
        timeout: float = 600.0,
        max_retries: int = 1,
        keep_alive: str | int | None = "30m",
        opener: Any | None = None,
        **_: Any,
    ) -> None:
        self._model_name = str(model_name or "").strip()
        self._base_url = self._normalize_base_url(base_url or _environment_value("OLLAMA_BASE_URL"))
        self._max_tokens = int(max_tokens) if max_tokens is not None else None
        self._timeout = float(timeout)
        self._max_retries = int(max_retries)
        self._keep_alive = keep_alive
        self._opener = opener or urllib.request.urlopen

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
        self._default_headers.setdefault("Accept", "application/json")
        self._default_headers.setdefault("User-Agent", "Auto-MU/ollama-native")

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
        if url.endswith("/v1"):
            url = url[:-3]
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

    def _request_json(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = dict(self._default_headers)
        data = None
        method = "GET"
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
            method = "POST"
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        for attempt in range(self._max_retries + 1):
            try:
                with self._opener(request, timeout=self._timeout) as response:
                    result = json.load(response)
                if not isinstance(result, dict):
                    raise RuntimeError(f"Ollama trả về dữ liệu không hợp lệ từ {path}")
                return result
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace").strip()
                if exc.code < 500 or attempt >= self._max_retries:
                    raise OllamaHTTPError(
                        exc.code,
                        f"Ollama HTTP {exc.code}: {detail or exc.reason}",
                        exc.headers,
                    ) from exc
            except urllib.error.URLError as exc:
                if attempt >= self._max_retries:
                    raise ConnectionError(f"Không kết nối được Ollama: {exc.reason}") from exc
            if attempt < self._max_retries:
                time.sleep(min(0.25 * (attempt + 1), 1.0))
        raise RuntimeError("Không kết nối được Ollama")

    def validate(self) -> None:
        available = set(self.available_models())
        if self._model_name not in available:
            choices = ", ".join(sorted(item for item in available if item)) or "không có"
            raise ValueError(f"Ollama model không tồn tại: {self._model_name}. Đang có: {choices}")

    def available_models(self) -> tuple[str, ...]:
        """Return the model names currently installed on the Ollama server."""
        available = {
            str(model.get("name") or model.get("model") or "").strip()
            for model in self._request_json("/api/tags").get("models", [])
            if isinstance(model, dict)
        }
        return tuple(sorted((item for item in available if item), key=str.casefold))

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
        return OllamaNativeChatSession(
            self._request_json,
            self._model_name,
            prompt,
            tools,
            max_tokens=self._max_tokens,
            keep_alive=self._keep_alive,
            history=history,
        )
