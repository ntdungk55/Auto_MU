from types import SimpleNamespace

from src.ai_control.ai_models.contracts import AIToolResult
from src.ai_control.ai_models.openrouter_adapter import OpenRouterModelAdapter
from src.ai_control.ai_tool_bridge import run_ai_mcp_turn


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.responses.pop(0))])


class _FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


class _FakeClientClass:
    def __init__(self, responses):
        self.responses = responses
        self.created = []

    def __call__(self, **kwargs):
        client = _FakeClient(self.responses)
        self.created.append((kwargs, client))
        return client


class _FakeMCPClient:
    def call_tool(self, name, arguments):
        return {"ok": True, "name": name, "arguments": arguments}


def _message(content="", tool_calls=None):
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
        model_dump=lambda **_: {"role": "assistant", "content": content},
    )


def test_openrouter_adapter_preserves_tool_call_ids_and_results():
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="get_companion_summoned_state", arguments="{}"),
    )
    client_class = _FakeClientClass([_message(tool_calls=[call]), _message("Đã kiểm tra.")])
    adapter = OpenRouterModelAdapter(
        api_key="test-key",
        model_name="google/gemini-2.5-flash",
        client_class=client_class,
    )

    chat = adapter.start_chat(
        system_prompt="System prompt",
        tools=[{"name": "get_companion_summoned_state", "input_schema": {"type": "object"}}],
    )
    first = chat.send(["Kiểm tra nhân vật phụ"])
    final = chat.send_tool_results(
        [AIToolResult(name="get_companion_summoned_state", call_id="call-1", result={"ok": True})]
    )

    assert first.tool_calls[0].call_id == "call-1"
    assert final.text == "Đã kiểm tra."
    _, client = client_class.created[0]
    assert client.chat.completions.requests[0]["tools"][0]["function"]["name"] == "get_companion_summoned_state"
    assert client.chat.completions.requests[0]["max_tokens"] == 4996
    assert client.chat.completions.requests[1]["messages"][-2]["tool_call_id"] == "call-1"


def test_openrouter_context_is_reset_after_a_completed_scenario():
    first_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="get_companion_summoned_state", arguments="{}"),
    )
    client_class = _FakeClientClass([_message(tool_calls=[first_call]), _message("Hoàn tất."), _message("Scenario mới.")])
    chat = OpenRouterModelAdapter(
        api_key="test-key",
        model_name="google/gemini-2.5-flash",
        client_class=client_class,
    ).start_chat(
        system_prompt="System prompt",
        tools=[{"name": "get_companion_summoned_state", "input_schema": {"type": "object"}}],
    )

    run_ai_mcp_turn(chat=chat, initial_content=["Scenario đầu"], mcp_client=_FakeMCPClient())
    chat.send(["Scenario tiếp theo"])

    _, client = client_class.created[0]
    next_messages = client.chat.completions.requests[2]["messages"]
    assert next_messages[:2] == [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": [{"type": "text", "text": "Scenario tiếp theo"}]},
    ]
    assert all("Scenario đầu" not in str(message) for message in next_messages)
    assert all("call-1" not in str(message) for message in next_messages)
