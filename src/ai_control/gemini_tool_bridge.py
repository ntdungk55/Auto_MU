"""Bridge dynamic MCP tool schemas and calls to the legacy Gemini SDK."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable


MAX_TOOL_CALLS_PER_MESSAGE = 20


@dataclass(frozen=True)
class GeminiMCPResult:
    text: str
    tool_call_count: int
    limit_reached: bool


def sanitize_json_schema(schema: Any) -> dict[str, Any]:
    """Convert JSON Schema from MCP to the subset accepted by google-generativeai."""
    if not isinstance(schema, dict):
        return {"type": "object"}

    if "anyOf" in schema or "oneOf" in schema:
        choices = schema.get("anyOf") or schema.get("oneOf") or []
        selected = next(
            (choice for choice in choices if isinstance(choice, dict) and choice.get("type") != "null"),
            {},
        )
        merged = dict(selected)
        if schema.get("description") and not merged.get("description"):
            merged["description"] = schema["description"]
        result = sanitize_json_schema(merged)
        if any(isinstance(choice, dict) and choice.get("type") == "null" for choice in choices):
            result["nullable"] = True
        return result

    raw_type = schema.get("type", "object")
    if isinstance(raw_type, list):
        nullable = "null" in raw_type
        raw_type = next((value for value in raw_type if value != "null"), "object")
    else:
        nullable = bool(schema.get("nullable", False))

    schema_type = str(raw_type or "object").lower()
    if schema_type not in {"object", "array", "string", "number", "integer", "boolean"}:
        schema_type = "string"

    result: dict[str, Any] = {"type": schema_type}
    description = str(schema.get("description") or schema.get("title") or "").strip()
    if description:
        result["description"] = description
    if nullable:
        result["nullable"] = True

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        result["enum"] = [str(value) for value in enum_values]

    if schema_type == "object":
        properties = schema.get("properties")
        if isinstance(properties, dict) and properties:
            result["properties"] = {
                str(name): sanitize_json_schema(value)
                for name, value in properties.items()
                if isinstance(value, dict)
            }
            required = schema.get("required")
            if isinstance(required, list):
                valid_required = [str(name) for name in required if str(name) in result["properties"]]
                if valid_required:
                    result["required"] = valid_required
    elif schema_type == "array":
        result["items"] = sanitize_json_schema(schema.get("items") or {"type": "string"})
        if isinstance(schema.get("minItems"), int):
            result["minItems"] = max(0, int(schema["minItems"]))
        if isinstance(schema.get("maxItems"), int):
            result["maxItems"] = max(0, int(schema["maxItems"]))

    return result


def build_gemini_tool_declarations(genai_module: Any, tools: list[dict[str, Any]]) -> list[Any]:
    """Create Gemini declarations for every tool returned by MCP tools/list."""
    declarations = []
    for tool in tools:
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        declarations.append(
            genai_module.types.FunctionDeclaration(
                name=name,
                description=str(tool.get("description") or f"MCP tool {name}"),
                parameters=sanitize_json_schema(tool.get("input_schema") or {"type": "object"}),
            )
        )
    return declarations


def tools_fingerprint(tools: list[dict[str, Any]]) -> str:
    return json.dumps(tools, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def extract_function_calls(response: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    try:
        candidates = list(getattr(response, "candidates", []) or [])
        if not candidates:
            return calls
        parts = list(getattr(getattr(candidates[0], "content", None), "parts", []) or [])
        for part in parts:
            function_call = getattr(part, "function_call", None)
            name = str(getattr(function_call, "name", "") or "").strip()
            if not name:
                continue
            try:
                payload = type(function_call).to_dict(function_call)
                arguments = payload.get("args", {})
            except Exception:
                arguments = dict(getattr(function_call, "args", {}) or {})
            calls.append({"name": name, "arguments": dict(arguments or {})})
    except Exception:
        return []
    return calls


def response_text(response: Any) -> str:
    try:
        return str(getattr(response, "text", "") or "").strip()
    except Exception:
        return ""


def run_gemini_mcp_turn(
    *,
    chat: Any,
    initial_content: Any,
    mcp_client: Any,
    genai_module: Any,
    max_tool_calls: int = MAX_TOOL_CALLS_PER_MESSAGE,
    on_tool_event: Callable[[dict[str, Any]], None] | None = None,
) -> GeminiMCPResult:
    """Compatibility wrapper over the provider-neutral AI/MCP loop."""
    from src.ai_control.ai_models.gemini_adapter import GeminiChatSession
    from src.ai_control.ai_tool_bridge import run_ai_mcp_turn

    result = run_ai_mcp_turn(
        chat=GeminiChatSession(chat, genai_module),
        initial_content=initial_content,
        mcp_client=mcp_client,
        max_tool_calls=max_tool_calls,
        on_tool_event=on_tool_event,
    )
    return GeminiMCPResult(result.text, result.tool_call_count, result.limit_reached)


def _emit_tool_event(callback: Callable[[dict[str, Any]], None] | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        pass
