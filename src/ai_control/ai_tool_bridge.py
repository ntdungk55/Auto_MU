"""Provider-neutral AI tool-call loop backed by dynamic MCP tools."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from src.ai_control.ai_models.contracts import AIChatSession, AIToolResult


MAX_TOOL_CALLS_PER_MESSAGE = 20


@dataclass(frozen=True)
class AIMCPResult:
    text: str
    tool_call_count: int
    limit_reached: bool


def tools_fingerprint(tools: list[dict[str, Any]]) -> str:
    return json.dumps(tools, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def run_ai_mcp_turn(
    *,
    chat: AIChatSession,
    initial_content: Any,
    mcp_client: Any,
    max_tool_calls: int = MAX_TOOL_CALLS_PER_MESSAGE,
    on_tool_event: Callable[[dict[str, Any]], None] | None = None,
) -> AIMCPResult:
    """Run one scenario turn and clear its dynamic context at every terminal outcome."""
    try:
        return _run_ai_mcp_turn(
            chat=chat,
            initial_content=initial_content,
            mcp_client=mcp_client,
            max_tool_calls=max_tool_calls,
            on_tool_event=on_tool_event,
        )
    finally:
        chat.reset_scenario()


def _run_ai_mcp_turn(
    *,
    chat: AIChatSession,
    initial_content: Any,
    mcp_client: Any,
    max_tool_calls: int = MAX_TOOL_CALLS_PER_MESSAGE,
    on_tool_event: Callable[[dict[str, Any]], None] | None = None,
) -> AIMCPResult:
    """Execute one scenario while retaining its dynamic messages for tool sequencing."""
    call_limit = max(1, int(max_tool_calls))
    tool_call_count = 0
    limit_reached = False
    response = chat.send(initial_content)

    while True:
        if not response.tool_calls:
            return AIMCPResult(response.text, tool_call_count, limit_reached)

        tool_results: list[AIToolResult] = []
        for call in response.tool_calls:
            name = call.name
            arguments = dict(call.arguments or {})
            if tool_call_count >= call_limit:
                limit_reached = True
                result = {
                    "ok": False,
                    "error": f"Đã đạt giới hạn {call_limit} MCP tool calls cho tin nhắn này",
                }
                _emit_tool_event(
                    on_tool_event,
                    {"phase": "limit", "name": name, "arguments": arguments, "result": result},
                )
            else:
                tool_call_count += 1
                _emit_tool_event(
                    on_tool_event,
                    {
                        "phase": "start",
                        "index": tool_call_count,
                        "limit": call_limit,
                        "name": name,
                        "arguments": arguments,
                    },
                )
                try:
                    result = mcp_client.call_tool(name, arguments)
                    if not isinstance(result, dict):
                        result = {"result": result}
                    phase = "error" if result.get("ok") is False or result.get("success") is False else "success"
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}
                    phase = "error"
                _emit_tool_event(
                    on_tool_event,
                    {
                        "phase": phase,
                        "index": tool_call_count,
                        "limit": call_limit,
                        "name": name,
                        "arguments": arguments,
                        "result": result,
                    },
                )
            tool_results.append(AIToolResult(name=name, result=result, call_id=call.call_id))

        response = chat.send_tool_results(tool_results)
        if limit_reached:
            text = response.text or f"Đã dừng vì đạt giới hạn {call_limit} MCP tool calls cho một tin nhắn."
            return AIMCPResult(text, tool_call_count, True)


def _emit_tool_event(callback: Callable[[dict[str, Any]], None] | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        pass
