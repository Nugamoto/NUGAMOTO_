from typing import Any

from .base import BaseClient


class UnitsClient(BaseClient):
    """Client for Units API operations."""

    BASE_PATH = "/v1/units"


    def list_units(self, unit_type: str | None = None) -> list[dict[str, Any]]:
        """Get all units with optional filtering."""
        params = {}
        if unit_type:
            params['unit_type'] = unit_type

        return self.get(self.BASE_PATH + "/", params=params)


    def get_unit(self, unit_id: int) -> dict[str, Any]:
        """Get single unit by ID."""
        return self.get(f"{self.BASE_PATH}/{unit_id}")


    def create_unit(self, unit_data: dict[str, Any]) -> dict[str, Any]:
        """Create new unit."""
        return self.post(self.BASE_PATH + "/", unit_data)


    def update_unit(self, unit_id: int, unit_data: dict[str, Any]) -> dict[str, Any]:
        """Update existing unit."""
        return self.patch(f"{self.BASE_PATH}/{unit_id}", unit_data)


    def delete_unit(self, unit_id: int) -> None:
        """Delete unit."""
        return self.delete(f"{self.BASE_PATH}/{unit_id}")


    def get_unit_conversions(self, unit_id: int) -> dict[str, Any]:
        """Get unit with available conversions."""
        return self.get(f"{self.BASE_PATH}/{unit_id}/conversions")


    def convert_value(self, from_unit_id: int, to_unit_id: int, value: float) -> dict[str, Any]:
        """Convert value between units."""
        return self.get(
            f"{self.BASE_PATH}/{from_unit_id}/convert-to/{to_unit_id}",
            params={"value": value}
        )


    def can_convert(self, from_unit_id: int, to_unit_id: int) -> dict[str, bool]:
        """Check if conversion between units is possible."""
        return self.get(f"{self.BASE_PATH}/{from_unit_id}/can-convert-to/{to_unit_id}")