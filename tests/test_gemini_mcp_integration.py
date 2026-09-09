from pathlib import Path
from types import SimpleNamespace
import sys

import google.generativeai as genai

from src.ai_control.gemini_tool_bridge import (
    build_gemini_tool_declarations,
    run_gemini_mcp_turn,
    sanitize_json_schema,
)
from src.ai_control.mcp_client_manager import MCPClientManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _tool_call_response(calls):
    parts = []
    for name, arguments in calls:
        function_call = genai.protos.FunctionCall(name=name, args=arguments)
        parts.append(SimpleNamespace(function_call=function_call))
    content = SimpleNamespace(parts=parts)
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)])


def _text_response(text):
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))])


class _FakeChat:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []

    def send_message(self, content):
        self.sent.append(content)
        return self.responses.pop(0)


class _FakeMCPClient:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"ok": True, "name": name, "arguments": arguments}


def test_schema_conversion_and_dynamic_declarations():
    schema = {
        "type": "object",
        "title": "Example",
        "additionalProperties": False,
        "properties": {
            "value": {"type": "string", "title": "Value", "default": "enter"},
        },
        "required": ["value"],
    }

    converted = sanitize_json_schema(schema)
    declarations = build_gemini_tool_declarations(
        genai,
        [{"name": "future_tool", "description": "Added later", "input_schema": schema}],
    )

    assert "additionalProperties" not in converted
    assert "default" not in converted["properties"]["value"]
    assert [declaration.name for declaration in declarations] == ["future_tool"]


def test_gemini_executes_mcp_tool_and_returns_final_text():
    chat = _FakeChat(
        [
            _tool_call_response([("create_keyboard_action", {"name": "Enter", "value": "enter"})]),
            _text_response("Đã tạo action."),
        ]
    )
    client = _FakeMCPClient()

    result = run_gemini_mcp_turn(
        chat=chat,
        initial_content=["Tạo action Enter"],
        mcp_client=client,
        genai_module=genai,
    )

    assert result.text == "Đã tạo action."
    assert result.tool_call_count == 1
    assert client.calls == [("create_keyboard_action", {"name": "Enter", "value": "enter"})]


def test_gemini_limits_execution_to_twenty_tool_calls():
    requested_calls = [("list_game_windows", {}) for _ in range(21)]
    chat = _FakeChat([_tool_call_response(requested_calls), _text_response("Đã dừng.")])
    client = _FakeMCPClient()

    result = run_gemini_mcp_turn(
        chat=chat,
        initial_content=["Kiểm tra nhiều lần"],
        mcp_client=client,
        genai_module=genai,
        max_tool_calls=20,
    )

    assert len(client.calls) == 20
    assert result.tool_call_count == 20
    assert result.limit_reached is True
    assert len(chat.sent[1]) == 21  # Includes an error response for the skipped call.


def test_real_stdio_manager_discovers_and_calls_tools_without_keypress():
    server_path = PROJECT_ROOT / "mcp" / "keyboard" / "server.py"
    manager = MCPClientManager(
        command=sys.executable,
        args=[str(server_path)],
        cwd=str(PROJECT_ROOT),
        startup_timeout_seconds=15,
    )
    manager.start()
    try:
        assert manager.wait_until_connected(15)
        tools = manager.refresh_tools()
        names = {tool["name"] for tool in tools}
        assert "create_keyboard_action" in names
        assert "run_keyboard_action" in names

        result = manager.call_tool(
            "create_keyboard_action",
            {"name": "Press Enter", "value": "enter", "delay_seconds": 0.1},
        )
        assert result["structuredContent"]["ok"] is True
    finally:
        manager.stop()

    assert manager.status_snapshot().state == "stopped"


def test_default_manager_aggregates_keyboard_and_process_servers():
    manager = MCPClientManager(startup_timeout_seconds=20)
    manager.start()
    try:
        assert manager.wait_until_connected(20)
        tools = manager.refresh_tools(20)
        names = {tool["name"] for tool in tools}
        assert "create_keyboard_action" in names
        assert "select_game_process" in names
        assert "get_selected_process_info" in names

        result = manager.call_tool("get_selected_process_info", {})
        assert "structuredContent" in result
    finally:
        manager.stop()

    assert manager.status_snapshot().state == "stopped"
