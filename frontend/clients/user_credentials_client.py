"""API client for User Credentials management."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class UserCredentialsClient(BaseClient):
    """Client for /v1/users/{user_id}/credentials endpoints."""

    BASE_PATH = "/v1/users"


    def create_user_credentials(self, user_id: int, credentials_data: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"{self.BASE_PATH}/{user_id}/credentials", json_data=credentials_data)


    def get_user_credentials(self, user_id: int) -> dict[str, Any]:
        return self.get(f"{self.BASE_PATH}/{user_id}/credentials")


    def update_user_credentials(self, user_id: int, credentials_data: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"{self.BASE_PATH}/{user_id}/credentials", json_data=credentials_data)


    def get_all_user_credentials_summary(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return self.get(f"{self.BASE_PATH}/credentials/summary", params={"skip": skip, "limit": limit})
