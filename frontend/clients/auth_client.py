from __future__ import annotations

from typing import Any

from .base import BaseClient


class AuthClient(BaseClient):
    """Auth API client for login, refresh and logout."""

    BASE_PATH = "/v1/auth"


    def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate and return token pair."""
        payload = {"email": email, "password": password}
        return self.post(f"{self.BASE_PATH}/login", json_data=payload)


    def register(self, name: str, email: str, password: str) -> dict[str, Any]:
        """Register a new user and return token pair (auto-login)."""
        payload = {"name": name, "email": email, "password": password}
        return self.post(f"{self.BASE_PATH}/register", json_data=payload)


    def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token using the refresh token."""
        # For simplicity we send raw refresh token in body (as implemented in backend)
        return self.post(f"{self.BASE_PATH}/refresh", data=refresh_token)


    def logout(self) -> None:
        """Stateless logout endpoint (client should clear tokens locally)."""
        self.post(f"{self.BASE_PATH}/logout")
