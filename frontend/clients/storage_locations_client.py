"""API client for Storage Locations management."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class StorageLocationsClient(BaseClient):
    """Client for Storage Locations API operations."""

    BASE_PATH = "/v1/storage-locations"


    def list_storage_locations(self, kitchen_id: int) -> list[dict[str, Any]]:
        """Get all storage locations for a specific kitchen."""
        params = {"kitchen_id": kitchen_id}
        return self.get(self.BASE_PATH + "/", params=params)


    def get_storage_location(self, location_id: int) -> dict[str, Any]:
        """Get a single storage location by ID."""
        return self.get(f"{self.BASE_PATH}/{location_id}")


    def create_storage_location(self, name: str, kitchen_id: int) -> dict[str, Any]:
        """Create a new storage location."""
        endpoint_with_params = f"{self.BASE_PATH}/?kitchen_id={kitchen_id}"
        location_data = {"name": name}
        return self.post(endpoint_with_params, json_data=location_data)


    def update_storage_location(
            self, location_id: int, location_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing storage location."""
        return self.patch(f"{self.BASE_PATH}/{location_id}", location_data)


    def delete_storage_location(self, location_id: int) -> None:
        """Delete a storage location."""
        self.delete(f"{self.BASE_PATH}/{location_id}")
