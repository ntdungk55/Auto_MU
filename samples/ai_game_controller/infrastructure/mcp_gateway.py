"""MCP client adapter."""

from __future__ import annotations

from typing import Any


class MCPGateway:
    """Expose MCP discovery and tool calls to the application layer."""

    def __init__(self, client_manager: Any) -> None:
        self.client_manager = client_manager

    def list_tools(self) -> list[dict[str, Any]]:
        """Return schemas discovered from every connected MCP server."""
        return self.client_manager.refresh_tools()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call one MCP tool through the shared client manager."""
        return self.client_manager.call_tool(name, arguments)
