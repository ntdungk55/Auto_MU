"""MCP server for user notifications."""

from __future__ import annotations

from typing import Any

try:
    from mcp.server import FastMCP
except ImportError:  # MCP 2.x
    from mcp.server import MCPServer as FastMCP

from src.logic.notifications.telegram import send_configured_message


mcp = FastMCP("Auto_MU Notifications")


@mcp.tool()
def send_telegram_message(message: str) -> dict[str, Any]:
    """Send an arbitrary text message through the configured Telegram bot."""
    text = str(message or "").strip()
    if not text:
        return {"success": False, "error": "message must be a non-empty string"}
    success, error = send_configured_message(text)
    return {"success": success, **({} if success else {"error": error or "Telegram send failed"})}


def run_notifications_mcp_server() -> None:
    """Run the notifications MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_notifications_mcp_server()
