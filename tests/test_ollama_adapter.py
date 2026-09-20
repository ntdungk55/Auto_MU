from __future__ import annotations

import io
import json

import pytest

from src.ai_control.ai_models.contracts import AIToolResult
import src.ai_control.ai_models.ollama_adapter as ollama_adapter_module
from src.ai_control.ai_models.ollama_adapter import OllamaModelAdapter


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class _FakeOpener:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def __call__(self, request, *, timeout):
        self.requests.append((request, timeout))
        payload = self._responses.pop(0)
        return _FakeResponse(json.dumps(payload).encode("utf-8"))


def _chat_response(content="", tool_calls=None, *, prompt_tokens=12, output_tokens=4):
    return {
        "message": {
            "role": "assistant",
            "content": content,
            **({"tool_calls": list(tool_calls)} if tool_calls else {}),
        },
        "prompt_eval_count": prompt_tokens,
        "eval_count": output_tokens,
    }


def _request_body(request):
    return json.loads(request.data.decode("utf-8")) if request.data else None


def test_ollama_adapter_uses_native_api_with_cloudflare_headers_and_tools():
    tool_call = {
        "function": {"name": "get_state", "arguments": {"target": "hero"}},
    }
    opener = _FakeOpener(
        [
            {"models": [{"name": "gemma4:e2b"}]},
            _chat_response(tool_calls=[tool_call]),
            _chat_response("done"),
        ]
    )
    adapter = OllamaModelAdapter(
        model_name="gemma4:e2b",
        base_url="https://myllm.mcp88.uk/v1",
        cf_access_client_id="client-id",
        cf_access_client_secret="client-secret",
        max_tokens=128,
        opener=opener,
    )

    adapter.validate()
    chat = adapter.start_chat(
        system_prompt="system",
        tools=[{"name": "get_state", "input_schema": {"type": "object"}}],
    )
    first = chat.send("inspect")
    final = chat.send_tool_results(
        [AIToolResult(name="get_state", call_id=first.tool_calls[0].call_id, result={"ok": True})]
    )

    tag_request, tag_timeout = opener.requests[0]
    first_chat_request, _ = opener.requests[1]
    second_chat_request, _ = opener.requests[2]
    first_body = _request_body(first_chat_request)
    second_body = _request_body(second_chat_request)

    assert adapter.provider_name == "ollama"
    assert adapter.base_url == "https://myllm.mcp88.uk"
    assert tag_request.full_url == "https://myllm.mcp88.uk/api/tags"
    assert tag_timeout == 600.0
    assert tag_request.get_header("Cf-access-client-id") == "client-id"
    assert tag_request.get_header("Cf-access-client-secret") == "client-secret"
    assert first.tool_calls[0].arguments == {"target": "hero"}
    assert first.usage.total_tokens == 16
    assert final.text == "done"
    assert first_chat_request.full_url == "https://myllm.mcp88.uk/api/chat"
    assert first_body["think"] is False
    assert first_body["keep_alive"] == "30m"
    assert first_body["options"] == {"num_predict": 128}
    assert first_body["tools"][0]["function"]["name"] == "get_state"
    assert second_body["messages"][-1] == {
        "role": "tool",
        "tool_name": "get_state",
        "content": '{"ok": true}',
    }


def test_ollama_adapter_rejects_unknown_model_during_validation():
    opener = _FakeOpener([{"models": [{"name": "gemma4:e2b"}]}])
    adapter = OllamaModelAdapter(
        model_name="missing",
        base_url="http://127.0.0.1:11434/v1",
        opener=opener,
    )

    with pytest.raises(ValueError, match="Ollama model không tồn tại"):
        adapter.validate()


def test_ollama_adapter_lists_only_current_server_models():
    opener = _FakeOpener(
        [{"models": [{"name": "z:model"}, {"model": "a:model"}, {"name": "z:model"}]}]
    )
    adapter = OllamaModelAdapter(
        model_name="discovery",
        base_url="http://127.0.0.1:11434",
        opener=opener,
    )

    assert adapter.available_models() == ("a:model", "z:model")


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
    opener = _FakeOpener([{"models": [{"name": "gemma4:e2b"}]}])

    adapter = OllamaModelAdapter(model_name="gemma4:e2b", opener=opener)
    adapter.validate()

    request, _ = opener.requests[0]
    assert request.full_url == "https://myllm.mcp88.uk/api/tags"
    assert request.get_header("Cf-access-client-id") == "stored-id"
    assert request.get_header("Cf-access-client-secret") == "stored-secret"
