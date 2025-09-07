"""API client for Kitchens."""

from __future__ import annotations
from typing import Any

from .base import BaseClient


class KitchensClient(BaseClient):
    """Client for /v1/kitchens endpoints."""

    BASE_PATH = "/v1/kitchens"

    # ---------- CRUD --------------------------------------------------
    def list_kitchens(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        params = {"skip": skip, "limit": limit}
        return self.get(self.BASE_PATH + "/", params=params)

    def get_kitchen(self, kitchen_id: int) -> dict[str, Any]:
        return self.get(f"{self.BASE_PATH}/{kitchen_id}")

    def create_kitchen(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(self.BASE_PATH + "/", json_data=payload)

    def update_kitchen(self, kitchen_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"{self.BASE_PATH}/{kitchen_id}", json_data=payload)

    def delete_kitchen(self, kitchen_id: int) -> None:
        self.delete(f"{self.BASE_PATH}/{kitchen_id}")