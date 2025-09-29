"""Model Context Protocol (MCP) server bootstrap helpers."""

from __future__ import annotations

from typing import Callable, List, Sequence

from fastapi import FastAPI

from backend.core.config import Settings, settings
from backend.main import app as fastapi_app

ToolRegistrationHook = Callable[[FastAPI, Settings], None]


class MCPServer:
    """Container for the FastAPI app and shared MCP configuration."""

    def __init__(self, app: FastAPI, config: Settings) -> None:
        self._app = app
        self._config = config
        self._tool_hooks: List[ToolRegistrationHook] = []

    @property
    def app(self) -> FastAPI:
        """Return the FastAPI application bound to the MCP server."""

        return self._app

    @property
    def config(self) -> Settings:
        """Return the shared configuration used by MCP integrations."""

        return self._config

    def register_tool(self, hook: ToolRegistrationHook) -> None:
        """Register a hook that can attach tools to the FastAPI app."""

        self._tool_hooks.append(hook)

    def register_tools(self, hooks: Sequence[ToolRegistrationHook]) -> None:
        """Register multiple tool hooks at once."""

        self._tool_hooks.extend(hooks)

    def initialize_tools(self) -> None:
        """Execute registered tool hooks."""

        for hook in self._tool_hooks:
            hook(self._app, self._config)


_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    """Return a singleton MCP server instance for deployments and tests."""

    global _server
    if _server is None:
        _server = MCPServer(app=fastapi_app, config=settings)
    return _server


def register_tool(hook: ToolRegistrationHook) -> None:
    """Convenience wrapper to register a tool against the global server."""

    get_mcp_server().register_tool(hook)


__all__ = ["MCPServer", "ToolRegistrationHook", "get_mcp_server", "register_tool"]
