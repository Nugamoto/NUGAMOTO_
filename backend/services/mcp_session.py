"""MCP Session Management Service.

Provides in-memory token storage for MCP tool authentication.
This allows MCP tools to maintain authentication state across multiple calls.
"""

from __future__ import annotations

from typing import Optional


class MCPSessionStore:
    """Simple in-memory token store for MCP sessions."""

    def __init__(self) -> None:
        """Initialize the session store."""
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._user_id: Optional[int] = None

    def set_tokens(self, access_token: str, refresh_token: str, user_id: int) -> None:
        """Store authentication tokens for MCP session.

        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token
            user_id: User ID associated with the tokens
        """
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._user_id = user_id

    def get_access_token(self) -> Optional[str]:
        """Get the stored access token.

        Returns:
            Access token or None if not set
        """
        return self._access_token

    def get_refresh_token(self) -> Optional[str]:
        """Get the stored refresh token.

        Returns:
            Refresh token or None if not set
        """
        return self._refresh_token

    def get_user_id(self) -> Optional[int]:
        """Get the stored user ID.

        Returns:
            User ID or None if not set
        """
        return self._user_id

    def clear(self) -> None:
        """Clear all stored tokens (logout)."""
        self._access_token = None
        self._refresh_token = None
        self._user_id = None

    def is_authenticated(self) -> bool:
        """Check if there's an active session.

        Returns:
            True if access token is present
        """
        return self._access_token is not None


# Global singleton instance for MCP sessions
_mcp_session = MCPSessionStore()


def get_mcp_session() -> MCPSessionStore:
    """Get the global MCP session store.

    Returns:
        Global MCP session store instance
    """
    return _mcp_session