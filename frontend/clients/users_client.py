"""API client for Users management."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class UsersClient(BaseClient):
    """Client for /v1/users endpoints."""

    BASE_PATH = "/v1/users"

    # ---------- CRUD -------------------------------------------------
    def list_users(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.get(self.BASE_PATH + "/", params={"limit": limit})

    def get_user(self, user_id: int) -> dict[str, Any]:
        return self.get(f"{self.BASE_PATH}/{user_id}")

    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        return self.post(self.BASE_PATH + "/", json_data=user_data)

    def update_user(self, user_id: int, user_data: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"{self.BASE_PATH}/{user_id}", json_data=user_data)

    def delete_user(self, user_id: int) -> None:
        self.delete(f"{self.BASE_PATH}/{user_id}")

    # ---------- User Management -------------------------------------
    def get_user_by_email(self, email: str) -> dict[str, Any]:
        return self.get(f"{self.BASE_PATH}/by-email", params={"email": email})

    def activate_user(self, user_id: int) -> dict[str, Any]:
        return self.post(f"{self.BASE_PATH}/{user_id}/activate")

    def deactivate_user(self, user_id: int) -> dict[str, Any]:
        return self.post(f"{self.BASE_PATH}/{user_id}/deactivate")

    def reset_password(self, user_id: int) -> dict[str, Any]:
        return self.post(f"{self.BASE_PATH}/{user_id}/reset-password")