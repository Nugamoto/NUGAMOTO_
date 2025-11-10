"""MCP Middleware for automatic token injection."""

from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.mcp_session import get_mcp_session


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to inject MCP session tokens into requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Inject MCP session token if available and no auth header present.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handlers
        """
        # Only inject token if:
        # 1. Request doesn't already have Authorization header
        # 2. MCP session has an active token
        # 3. Request is to a protected endpoint (not auth endpoints)

        has_auth_header = "authorization" in request.headers
        is_auth_endpoint = request.url.path.startswith("/v1/auth/")

        if not has_auth_header and not is_auth_endpoint:
            mcp_session = get_mcp_session()
            access_token = mcp_session.get_access_token()

            if access_token:
                # Create mutable headers and add authorization
                mutable_headers = dict(request.headers)
                mutable_headers["authorization"] = f"Bearer {access_token}"

                # Update request scope with new headers
                request._headers = mutable_headers  # type: ignore
                request.scope["headers"] = [
                    (k.lower().encode(), v.encode())
                    for k, v in mutable_headers.items()
                ]

        response = await call_next(request)
        return response