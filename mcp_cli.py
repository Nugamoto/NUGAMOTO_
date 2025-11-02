"""MCP Client for FastAPI-MCP endpoint."""

from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import asynccontextmanager
from getpass import getpass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from mcp.client.sse import sse_client
from mcp.types import Tool
from requests.exceptions import HTTPError, RequestException

DEFAULT_SERVER_URL = "http://localhost:8000/mcp"


def derive_api_base(server_url: str) -> str:
    """Derive the REST API base URL from the MCP server URL."""
    parsed = urlparse(server_url)
    base_path = (parsed.path or "").rstrip("/")
    if base_path.endswith("/mcp"):
        base_path = base_path[: -len("/mcp")]
    base_path = base_path.rstrip("/")
    if base_path:
        return f"{parsed.scheme}://{parsed.netloc}{base_path}"
    return f"{parsed.scheme}://{parsed.netloc}"


@asynccontextmanager
async def session_scope(server_url: str, token: str | None = None):
    """Create and manage an MCP client session using SSE."""
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with sse_client(server_url, headers=headers) as session:
        await session.initialize()
        yield session


async def list_tools(server_url: str, token: str | None = None) -> list[Tool]:
    """Fetch and print the available tools from the MCP server."""
    async with session_scope(server_url, token) as session:
        result = await session.list_tools()
        tools = result.tools

        if not tools:
            print("No tools available.")
        else:
            print(f"\n📋 Available Tools ({len(tools)} total):\n")
            for tool in tools:
                description = tool.description or "No description"
                print(f"  🔧 {tool.name}")
                print(f"     {description}")
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    props = tool.inputSchema.get("properties", {})
                    if props:
                        print(f"     Parameters: {', '.join(props.keys())}")
                print()

        return tools


def _parse_arguments_json(raw: str | None) -> dict[str, Any]:
    """Parse JSON arguments string, return empty dict if None."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for arguments: {exc}") from exc


async def call_tool(
    server_url: str,
    tool_name: str,
    *,
    arguments: str | None = None,
    token: str | None = None,
) -> None:
    """Invoke a specific MCP tool and pretty-print the response."""
    payload = _parse_arguments_json(arguments)

    async with session_scope(server_url, token) as session:
        try:
            result = await session.call_tool(tool_name, payload)
            print(json.dumps(result.model_dump(mode="json"), indent=2))
        except Exception as e:
            print(f"❌ Error calling tool '{tool_name}': {e}")


async def repl(server_url: str, tool_name: str, token: str | None = None) -> None:
    """Interactive REPL for repeatedly calling a tool."""
    print(f"🔄 Starting MCP tool REPL for '{tool_name}'")
    print("   Type 'q' to quit, or press Enter to call the tool.\n")

    async with session_scope(server_url, token) as session:
        while True:
            user_input = await asyncio.to_thread(input, f"Call '{tool_name}'? [Enter/q] ")
            if user_input.strip().lower() in {"q", "quit", "exit"}:
                print("👋 Exiting REPL.")
                break

            try:
                result = await session.call_tool(tool_name, {})
                print(json.dumps(result.model_dump(mode="json"), indent=2))
            except Exception as e:
                print(f"❌ Error: {e}")


def _perform_login_request(api_base_url: str, email: str, password: str) -> dict[str, Any]:
    """Perform login request against REST API."""
    login_url = f"{api_base_url.rstrip('/')}/v1/auth/login"
    response = requests.post(
        login_url,
        json={"email": email, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


async def login(
    api_base_url: str,
    email: str | None,
    password: str | None,
    *,
    save_path: str | None = None,
) -> None:
    """Authenticate and fetch tokens from REST API."""
    resolved_email = email or await asyncio.to_thread(input, "📧 Email: ")
    resolved_password = password or await asyncio.to_thread(getpass, "🔐 Password: ")

    try:
        payload = await asyncio.to_thread(
            _perform_login_request, api_base_url, resolved_email, resolved_password
        )
    except HTTPError as exc:
        status_code = exc.response.status_code if exc.response else "unknown"
        detail = exc.response.text if exc.response else str(exc)
        print(f"❌ Login failed (status {status_code}): {detail}")
        return
    except RequestException as exc:
        print(f"❌ Failed to contact API: {exc}")
        return

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    token_type = payload.get("token_type", "bearer")

    if not access_token:
        print("❌ Login response did not include an access token.")
        return

    print(f"\n✅ Login successful!")
    print(f"   Token type: {token_type}")
    print(f"   Access token: {access_token[:20]}...")
    if refresh_token:
        print(f"   Refresh token: {refresh_token[:20]}...")

    if save_path:
        path = Path(save_path).expanduser()
        try:
            path.write_text(access_token)
            print(f"   💾 Access token saved to {path}")
        except OSError as exc:
            print(f"❌ Could not save token to {path}: {exc}")


def add_token_option(subparser: argparse.ArgumentParser) -> None:
    """Add --token option to subparser."""
    subparser.add_argument(
        "--token",
        help="Bearer token for authenticated requests",
        default=None,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="MCP Client for FastAPI-MCP servers",
        epilog="Use 'mcp_cli <command> --help' for more info on a specific command.",
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER_URL,
        help=f"MCP server URL (default: {DEFAULT_SERVER_URL})",
    )
    parser.add_argument(
        "--api",
        default=None,
        help="Base REST API URL (auto-derived from --server if not specified)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all available MCP tools")
    add_token_option(list_parser)

    # call command
    call_parser = subparsers.add_parser("call", help="Call a specific MCP tool")
    call_parser.add_argument(
        "name",
        nargs="?",
        default="get_service_status",
        help="Tool name to call (default: get_service_status)",
    )
    call_parser.add_argument(
        "--arguments",
        help="JSON string with tool arguments",
        default=None,
    )
    add_token_option(call_parser)

    # repl command
    repl_parser = subparsers.add_parser("repl", help="Interactive REPL for a tool")
    repl_parser.add_argument(
        "name",
        nargs="?",
        default="get_service_status",
        help="Tool name to use in REPL",
    )
    add_token_option(repl_parser)

    # login command
    login_parser = subparsers.add_parser("login", help="Authenticate and fetch tokens")
    login_parser.add_argument("--email", help="Account email", default=None)
    login_parser.add_argument("--password", help="Account password", default=None)
    login_parser.add_argument(
        "--save-token",
        help="File path to store the access token",
        default=None,
    )

    return parser


async def async_main() -> None:
    """Async main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    server_url: str = args.server
    api_base_url: str = args.api or derive_api_base(server_url)
    token = getattr(args, "token", None)

    if args.command == "list":
        await list_tools(server_url, token=token)
    elif args.command == "call":
        await call_tool(server_url, args.name, arguments=args.arguments, token=token)
    elif args.command == "repl":
        await repl(server_url, args.name, token=token)
    elif args.command == "login":
        await login(api_base_url, args.email, args.password, save_path=args.save_token)
    else:
        parser.error(f"Unknown command: {args.command}")


def main() -> None:
    """Main entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()