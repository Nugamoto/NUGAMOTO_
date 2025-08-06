"""API client for Inventory-Items management."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class InventoryItemsClient(BaseClient):
    """Client for Inventory Items API operations."""

    BASE_PATH = "/v1/items"

    # ---------- CRUD -------------------------------------------------

    def list_inventory_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        """Return all inventory items for a kitchen."""
        params = {"kitchen_id": kitchen_id}
        return self.get(self.BASE_PATH + "/", params=params)

    def get_inventory_item(self, item_id: int) -> dict[str, Any]:
        """Return a single inventory item by ID."""
        return self.get(f"{self.BASE_PATH}/{item_id}")

    def create_or_update_item(self, kitchen_id: int, item_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new inventory item or update an existing one.

        kitchen_id is required as URL-query parameter, the payload goes into the body.
        """
        endpoint = f"{self.BASE_PATH}/?kitchen_id={kitchen_id}"
        return self.post(endpoint, json_data=item_data)

    def update_item_details(self, item_id: int, item_data: dict[str, Any]) -> dict[str, Any]:
        """PATCH an existing inventory item."""
        return self.patch(f"{self.BASE_PATH}/{item_id}", json_data=item_data)

    def delete_item(self, item_id: int) -> None:
        """Delete an inventory item."""
        self.delete(f"{self.BASE_PATH}/{item_id}")

    # ---------- Analysis ---------------------------------------------

    def get_low_stock_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        params = {"kitchen_id": kitchen_id}
        return self.get(f"{self.BASE_PATH}/analysis/low-stock", params=params)

    def get_expiring_items(self, kitchen_id: int, threshold_days: int = 7) -> list[dict[str, Any]]:
        params = {"kitchen_id": kitchen_id, "threshold_days": threshold_days}
        return self.get(f"{self.BASE_PATH}/analysis/expiring", params=params)

    def get_expired_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        params = {"kitchen_id": kitchen_id}
        return self.get(f"{self.BASE_PATH}/analysis/expired", params=params)