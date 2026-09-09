"""Persistent multi-server MCP stdio client owned by Auto_MU."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
import os
from pathlib import Path
import threading
from typing import Any, Callable, Coroutine

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import mcp.types as mcp_types

from src.ai_control.server_registry import MCPServerSpec, default_server_specs
from src.logic.app_paths import get_runtime_root


@dataclass(frozen=True)
class MCPStatus:
    state: str
    message: str
    tool_count: int


class MCPClientManager:
    """Start, monitor, aggregate and route tools from local MCP servers."""

    def __init__(
        self,
        *,
        server_specs: list[MCPServerSpec] | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        cwd: str | None = None,
        startup_timeout_seconds: float = 20.0,
        tool_timeout_seconds: float = 45.0,
    ) -> None:
        if server_specs is not None:
            specs = list(server_specs)
        elif command is not None or args is not None or cwd is not None:
            default = default_server_specs()[0]
            specs = [
                MCPServerSpec(
                    "custom",
                    command or default.command,
                    tuple(args) if args is not None else default.args,
                    cwd or default.cwd,
                )
            ]
        else:
            specs = default_server_specs()
        if not specs:
            raise ValueError("Cần ít nhất một MCP server")
        names = [spec.name for spec in specs]
        if len(names) != len(set(names)):
            raise ValueError("Tên MCP server không được trùng nhau")

        self._server_specs = tuple(specs)
        self._startup_timeout_seconds = max(1.0, float(startup_timeout_seconds))
        self._tool_timeout_seconds = max(1.0, float(tool_timeout_seconds))

        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._sessions: dict[str, ClientSession] = {}
        self._server_tools: dict[str, list[dict[str, Any]]] = {}
        self._tools: list[dict[str, Any]] = []
        self._tool_routes: dict[str, str] = {}
        self._collisions: set[str] = set()
        self._server_errors: dict[str, str] = {}
        self._status = MCPStatus("stopped", "MCP chưa chạy", 0)
        self._connected = threading.Event()
        self._available = threading.Event()
        self._stop_requested = threading.Event()
        self._reconnect_requested: set[str] = set()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_requested.clear()
            self._reconnect_requested.clear()
            self._status = MCPStatus("starting", "Đang khởi động MCP servers…", len(self._tools))
            self._thread = threading.Thread(target=self._thread_main, name="auto-mu-mcp-client", daemon=True)
            self._thread.start()

    def stop(self, timeout_seconds: float = 8.0) -> None:
        self._stop_requested.set()
        with self._lock:
            self._reconnect_requested.update(spec.name for spec in self._server_specs)
            loop = self._loop
            thread = self._thread
            self._status = MCPStatus("stopping", "Đang dừng MCP servers…", len(self._tools))
        if loop is not None:
            try:
                loop.call_soon_threadsafe(lambda: None)
            except RuntimeError:
                pass
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.1, float(timeout_seconds)))
        with self._lock:
            if thread is not None and thread.is_alive():
                self._status = MCPStatus("error", "MCP servers chưa dừng kịp thời", len(self._tools))
            else:
                self._thread = None
                self._status = MCPStatus("stopped", "MCP đã dừng", 0)

    def status_snapshot(self) -> MCPStatus:
        with self._lock:
            return self._status

    def cached_tools(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(tool) for tool in self._tools]

    def wait_until_connected(self, timeout_seconds: float | None = None) -> bool:
        timeout = self._startup_timeout_seconds if timeout_seconds is None else max(0.0, float(timeout_seconds))
        return self._connected.wait(timeout)

    def refresh_tools(self, timeout_seconds: float | None = None) -> list[dict[str, Any]]:
        timeout = self._startup_timeout_seconds if timeout_seconds is None else max(1.0, float(timeout_seconds))
        try:
            return self._run_on_client_loop(self._refresh_all_tools_async, timeout)
        except Exception:
            cached = self.cached_tools()
            if cached:
                return cached
            raise

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        tool_name = str(name or "").strip()
        if not tool_name:
            raise ValueError("Tên MCP tool không được để trống")
        with self._lock:
            server_name = self._tool_routes.get(tool_name)
            collision = tool_name in self._collisions
        if collision:
            raise ValueError(f"MCP tool bị trùng tên giữa các server: {tool_name}")
        if server_name is None:
            raise ValueError(f"MCP tool không tồn tại: {tool_name}")

        request_timeout = self._tool_timeout_seconds if timeout_seconds is None else max(1.0, float(timeout_seconds))

        async def invoke() -> dict[str, Any]:
            session = self._require_session(server_name)
            result = await session.call_tool(
                tool_name,
                arguments=dict(arguments or {}),
                read_timeout_seconds=request_timeout,
            )
            if hasattr(result, "model_dump"):
                return result.model_dump(mode="json", by_alias=True, exclude_none=True)
            return {"result": str(result)}

        try:
            return self._run_on_client_loop(invoke, request_timeout + 5.0)
        except Exception:
            self._request_reconnect(server_name)
            raise

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run_forever())
        except Exception as exc:
            with self._lock:
                self._status = MCPStatus("error", f"MCP client lỗi: {exc}", len(self._tools))
        finally:
            self._connected.clear()
            self._available.clear()
            with self._lock:
                self._loop = None
                self._sessions.clear()
                if self._stop_requested.is_set():
                    self._status = MCPStatus("stopped", "MCP đã dừng", 0)

    async def _run_forever(self) -> None:
        with self._lock:
            self._loop = asyncio.get_running_loop()
        tasks = [asyncio.create_task(self._server_worker(spec), name=f"mcp-{spec.name}") for spec in self._server_specs]
        try:
            while not self._stop_requested.is_set():
                await asyncio.sleep(0.1)
        finally:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _server_worker(self, spec: MCPServerSpec) -> None:
        while not self._stop_requested.is_set():
            with self._lock:
                self._reconnect_requested.discard(spec.name)
            try:
                await self._run_server_connection(spec)
            except Exception as exc:
                if not self._stop_requested.is_set():
                    with self._lock:
                        self._server_errors[spec.name] = str(exc)
                        self._update_status_locked()
            finally:
                self._remove_server(spec.name)
            if not self._stop_requested.is_set():
                await asyncio.sleep(1.0)

    async def _run_server_connection(self, spec: MCPServerSpec) -> None:
        env = os.environ.copy()
        env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"})
        params = StdioServerParameters(
            command=spec.command,
            args=list(spec.args),
            cwd=spec.cwd,
            env=env,
            encoding="utf-8",
            encoding_error_handler="replace",
        )

        log_dir = Path(get_runtime_root()) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / f"mcp_{spec.name}_server.log", "a", encoding="utf-8") as errlog:
            async with stdio_client(params, errlog=errlog) as streams:
                read_stream, write_stream = streams
                async with ClientSession(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=self._tool_timeout_seconds,
                ) as session:
                    await asyncio.wait_for(session.initialize(), timeout=self._startup_timeout_seconds)
                    tools = await self._list_tools(session, spec.name)
                    with self._lock:
                        self._sessions[spec.name] = session
                        self._server_tools[spec.name] = tools
                        self._server_errors.pop(spec.name, None)
                        self._rebuild_tool_index_locked()
                        self._update_status_locked()

                    while not self._stop_requested.is_set():
                        with self._lock:
                            reconnect = spec.name in self._reconnect_requested
                        if reconnect:
                            break
                        await asyncio.sleep(0.1)

    async def _list_tools(self, session: ClientSession, server_name: str) -> list[dict[str, Any]]:
        discovered: list[dict[str, Any]] = []
        params: mcp_types.PaginatedRequestParams | None = None
        for _ in range(100):
            result = await session.list_tools(params=params)
            for tool in result.tools:
                discovered.append(
                    {
                        "name": str(tool.name),
                        "description": str(tool.description or ""),
                        "input_schema": dict(tool.input_schema or {"type": "object"}),
                        "server_name": server_name,
                    }
                )
            cursor = result.next_cursor
            if not cursor:
                return discovered
            params = mcp_types.PaginatedRequestParams(cursor=cursor)
        raise RuntimeError(f"MCP tools/list của {server_name} vượt quá 100 trang")

    async def _refresh_all_tools_async(self) -> list[dict[str, Any]]:
        with self._lock:
            sessions = dict(self._sessions)
        if not sessions:
            raise RuntimeError("MCP chưa kết nối server nào")

        names = list(sessions)
        results = await asyncio.gather(
            *(self._list_tools(sessions[name], name) for name in names),
            return_exceptions=True,
        )
        failures: list[Exception] = []
        with self._lock:
            for name, result in zip(names, results):
                if isinstance(result, BaseException):
                    failures.append(result if isinstance(result, Exception) else RuntimeError(str(result)))
                    self._server_errors[name] = str(result)
                    self._reconnect_requested.add(name)
                else:
                    self._server_tools[name] = result
                    self._server_errors.pop(name, None)
            self._rebuild_tool_index_locked()
            self._update_status_locked()
            tools = [dict(tool) for tool in self._tools]
        if not tools and failures:
            raise failures[0]
        return tools

    def _rebuild_tool_index_locked(self) -> None:
        by_name: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for server_name, tools in self._server_tools.items():
            for tool in tools:
                by_name.setdefault(str(tool["name"]), []).append((server_name, tool))

        self._collisions = {name for name, owners in by_name.items() if len(owners) > 1}
        self._tool_routes = {
            name: owners[0][0]
            for name, owners in by_name.items()
            if len(owners) == 1
        }
        self._tools = sorted(
            (dict(owners[0][1]) for name, owners in by_name.items() if name not in self._collisions),
            key=lambda tool: (str(tool.get("server_name", "")), str(tool["name"])),
        )

    def _remove_server(self, server_name: str) -> None:
        with self._lock:
            self._sessions.pop(server_name, None)
            self._server_tools.pop(server_name, None)
            self._rebuild_tool_index_locked()
            self._update_status_locked()

    def _update_status_locked(self) -> None:
        connected = len(self._sessions)
        total = len(self._server_specs)
        if connected:
            self._available.set()
        else:
            self._available.clear()
        if connected == total:
            self._connected.set()
        else:
            self._connected.clear()

        if self._collisions:
            names = ", ".join(sorted(self._collisions))
            self._status = MCPStatus("error", f"Trùng tên MCP tool: {names}", len(self._tools))
        elif connected == total:
            self._status = MCPStatus("connected", f"MCP đã kết nối {connected}/{total} server", len(self._tools))
        elif connected > 0:
            self._status = MCPStatus("degraded", f"MCP chỉ kết nối {connected}/{total} server", len(self._tools))
        elif self._server_errors:
            details = "; ".join(f"{name}: {error}" for name, error in sorted(self._server_errors.items()))
            self._status = MCPStatus("error", f"MCP chưa kết nối: {details}", 0)
        elif not self._stop_requested.is_set():
            self._status = MCPStatus("starting", "Đang kết nối MCP servers…", 0)

    def _run_on_client_loop(
        self,
        coroutine_factory: Callable[[], Coroutine[Any, Any, Any]],
        timeout_seconds: float,
    ) -> Any:
        if not self._available.wait(timeout=min(timeout_seconds, self._startup_timeout_seconds)):
            raise RuntimeError(self.status_snapshot().message)
        with self._lock:
            loop = self._loop
        if loop is None or loop.is_closed():
            raise RuntimeError("MCP event loop không hoạt động")

        future = asyncio.run_coroutine_threadsafe(coroutine_factory(), loop)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"MCP timeout sau {timeout_seconds:.0f}s") from exc

    def _require_session(self, server_name: str) -> ClientSession:
        with self._lock:
            session = self._sessions.get(server_name)
        if session is None:
            raise RuntimeError(f"MCP server chưa kết nối: {server_name}")
        return session

    def _request_reconnect(self, server_name: str) -> None:
        with self._lock:
            self._reconnect_requested.add(server_name)
            loop = self._loop
        if loop is not None:
            try:
                loop.call_soon_threadsafe(lambda: None)
            except RuntimeError:
                pass
