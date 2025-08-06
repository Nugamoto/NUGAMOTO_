"""API client for Inventory-Items management."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class InventoryItemsClient(BaseClient):
    """Client for /v1/items endpoints."""

    BASE_PATH = "/v1/items"

    # ---------- CRUD -------------------------------------------------
    def list_inventory_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        return self.get(self.BASE_PATH + "/", params={"kitchen_id": kitchen_id})

    def get_inventory_item(self, item_id: int) -> dict[str, Any]:
        return self.get(f"{self.BASE_PATH}/{item_id}")


    def create_or_update_item(
            self, kitchen_id: int, item_data: dict[str, Any]
    ) -> dict[str, Any]:
        endpoint = f"{self.BASE_PATH}/?kitchen_id={kitchen_id}"
        return self.post(endpoint, json_data=item_data)


    def update_item_details(
            self, item_id: int, item_data: dict[str, Any]
    ) -> dict[str, Any]:
        return self.patch(f"{self.BASE_PATH}/{item_id}", json_data=item_data)

    def delete_item(self, item_id: int) -> None:
        self.delete(f"{self.BASE_PATH}/{item_id}")


    # ---------- Analysis --------------------------------------------
    def get_low_stock_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        return self.get(f"{self.BASE_PATH}/analysis/low-stock",
                        params={"kitchen_id": kitchen_id})


    def get_expiring_items(self,
                           kitchen_id: int,
                           threshold_days: int = 7) -> list[dict[str, Any]]:
        return self.get(f"{self.BASE_PATH}/analysis/expiring",
                        params={"kitchen_id": kitchen_id,
                                "threshold_days": threshold_days})

    def get_expired_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        return self.get(f"{self.BASE_PATH}/analysis/expired",
                        params={"kitchen_id": kitchen_id})
