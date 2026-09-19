from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.ai_control.ai_models.contracts import AIToolResult
import src.ai_control.ai_models.ollama_adapter as ollama_adapter_module
from src.ai_control.ai_models.ollama_adapter import OllamaModelAdapter


class _FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        message, usage = self._responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class _FakeClient:
    def __init__(self, models, responses):
        self.models = SimpleNamespace(
            list=lambda: SimpleNamespace(data=[SimpleNamespace(id=model) for model in models])
        )
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


class _FakeClientClass:
    def __init__(self, models, responses):
        self._models = models
        self._responses = responses
        self.created = []

    def __call__(self, **kwargs):
        client = _FakeClient(self._models, self._responses)
        self.created.append((kwargs, client))
        return client


def _response(content="", tool_calls=None, *, prompt_tokens=12, completion_tokens=4):
    message = SimpleNamespace(
        content=content,
        tool_calls=list(tool_calls or []),
        model_dump=lambda **_: {
            "role": "assistant",
            "content": content,
            **({"tool_calls": list(tool_calls)} if tool_calls else {}),
        },
    )
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return message, usage


def test_ollama_adapter_uses_openai_client_with_cloudflare_headers_and_tools():
    tool_call = SimpleNamespace(
        id="call-ollama-1",
        function=SimpleNamespace(name="get_state", arguments='{"target":"hero"}'),
    )
    client_class = _FakeClientClass(
        ["gemma4:e2b"],
        [_response(tool_calls=[tool_call]), _response("done")],
    )
    adapter = OllamaModelAdapter(
        model_name="gemma4:e2b",
        base_url="https://myllm.mcp88.uk",
        cf_access_client_id="client-id",
        cf_access_client_secret="client-secret",
        client_class=client_class,
    )

    adapter.validate()
    chat = adapter.start_chat(
        system_prompt="system",
        tools=[{"name": "get_state", "input_schema": {"type": "object"}}],
    )
    first = chat.send("inspect")
    final = chat.send_tool_results(
        [AIToolResult(name="get_state", call_id="call-ollama-1", result={"ok": True})]
    )

    client_args, client = client_class.created[0]
    assert adapter.provider_name == "ollama"
    assert adapter.base_url == "https://myllm.mcp88.uk/v1"
    assert client_args["api_key"] == "ollama"
    assert client_args["default_headers"] == {
        "CF-Access-Client-Id": "client-id",
        "CF-Access-Client-Secret": "client-secret",
    }
    assert first.tool_calls[0].arguments == {"target": "hero"}
    assert first.usage.total_tokens == 16
    assert final.text == "done"
    assert client.chat.completions.requests[0]["tools"][0]["function"]["name"] == "get_state"
    assert client.chat.completions.requests[0]["extra_body"] == {"think": False}
    assert client.chat.completions.requests[1]["messages"][-2]["tool_call_id"] == "call-ollama-1"


def test_ollama_adapter_rejects_unknown_model_during_validation():
    client_class = _FakeClientClass(["gemma4:e2b"], [])
    adapter = OllamaModelAdapter(
        model_name="missing",
        base_url="http://127.0.0.1:11434/v1",
        client_class=client_class,
    )

    with pytest.raises(ValueError, match="Ollama model không tồn tại"):
        adapter.validate()


def test_ollama_adapter_requires_complete_cloudflare_credentials():
    with pytest.raises(ValueError, match="Client ID và Client Secret"):
        OllamaModelAdapter(
            model_name="gemma4:e2b",
            cf_access_client_id="only-id",
            cf_access_client_secret="",
        )


def test_ollama_adapter_uses_persistent_environment_when_process_values_are_missing(monkeypatch):
    values = {
        "OLLAMA_BASE_URL": "https://myllm.mcp88.uk/v1",
        "CF_ACCESS_CLIENT_ID": "stored-id",
        "CF_ACCESS_CLIENT_SECRET": "stored-secret",
    }
    monkeypatch.setattr(ollama_adapter_module, "_environment_value", values.get)
    client_class = _FakeClientClass(["gemma4:e2b"], [])

    adapter = OllamaModelAdapter(model_name="gemma4:e2b", client_class=client_class)
    adapter.validate()

    client_args, _ = client_class.created[0]
    assert client_args["base_url"] == "https://myllm.mcp88.uk/v1"
    assert client_args["default_headers"] == {
        "CF-Access-Client-Id": "stored-id",
        "CF-Access-Client-Secret": "stored-secret",
    }
