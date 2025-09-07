from __future__ import annotations

from typing import Any

from .base import BaseClient


class InventoryItemsClient(BaseClient):
    """Client for /v1/items endpoints."""

    BASE_PATH = "/v1/items"

    # ---------- CRUD -------------------------------------------------
    def list_inventory_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        """List all inventory items for a given kitchen."""
        return self.get(self.BASE_PATH + "/", params={"kitchen_id": kitchen_id})

    def get_inventory_item(self, item_id: int) -> dict[str, Any]:
        """Get a single inventory item by its ID."""
        return self.get(f"{self.BASE_PATH}/{item_id}")

    def create_or_update_item(
            self,
            kitchen_id: int,
            item_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new item or merge into an existing item (same food+location)."""
        endpoint = f"{self.BASE_PATH}/?kitchen_id={kitchen_id}"
        return self.post(endpoint, json_data=item_data)

    def update_item_details(
            self,
            item_id: int,
            item_data: dict[str, Any],
            *,
            kitchen_id: int,
    ) -> dict[str, Any]:
        """Update an existing inventory item (PATCH requires kitchen_id as query)."""
        return self.patch(
            f"{self.BASE_PATH}/{item_id}",
            json_data=item_data,
            params={"kitchen_id": kitchen_id},
        )


    def delete_item(self, item_id: int, *, kitchen_id: int) -> None:
        """Delete an inventory item (DELETE requires kitchen_id as query)."""
        self.delete(f"{self.BASE_PATH}/{item_id}?kitchen_id={kitchen_id}")

    # ---------- Analysis --------------------------------------------
    def get_low_stock_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        """Get items that are below their minimum quantity."""
        return self.get(
            f"{self.BASE_PATH}/analysis/low-stock",
            params={"kitchen_id": kitchen_id},
        )


    def get_expiring_items(
            self,
            kitchen_id: int,
            threshold_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get items expiring within threshold_days."""
        return self.get(
            f"{self.BASE_PATH}/analysis/expiring",
            params={"kitchen_id": kitchen_id, "threshold_days": threshold_days},
        )

    def get_expired_items(self, kitchen_id: int) -> list[dict[str, Any]]:
        """Get items already expired."""
        return self.get(
            f"{self.BASE_PATH}/analysis/expired",
            params={"kitchen_id": kitchen_id},
        )
