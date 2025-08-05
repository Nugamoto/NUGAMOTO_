# frontend/clients/food_items_client.py
from typing import Any

from base import BaseClient


class FoodItemsClient(BaseClient):
    """Client for Food Items API operations."""

    BASE_PATH = "/v1/food-items"


    def list_food_items(self, category: str | None = None,
                        skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get all food items with optional filtering."""
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        if category:
            params['category'] = category

        return self.get(self.BASE_PATH + "/", params=params)


    def get_food_item(self, food_item_id: int) -> dict[str, Any]:
        """Get single food item by ID."""
        return self.get(f"{self.BASE_PATH}/{food_item_id}")


    def create_food_item(self, food_item_data: dict[str, Any]) -> dict[str, Any]:
        """Create new food item."""
        return self.post(self.BASE_PATH + "/", food_item_data)


    def update_food_item(self, food_item_id: int, food_item_data: dict[str, Any]) -> dict[str, Any]:
        """Update existing food item."""
        return self.patch(f"{self.BASE_PATH}/{food_item_id}", food_item_data)


    def delete_food_item(self, food_item_id: int) -> None:
        """Delete food item."""
        return self.delete(f"{self.BASE_PATH}/{food_item_id}")


    def get_food_item_with_conversions(self, food_item_id: int) -> dict[str, Any]:
        """Get food item with unit conversions."""
        return self.get(f"{self.BASE_PATH}/{food_item_id}/with-conversions")


    def get_food_item_with_aliases(self, food_item_id: int,
                                   user_id: int | None = None) -> dict[str, Any]:
        """Get food item with aliases."""
        params: dict[str, Any] = {}
        if user_id:
            params['user_id'] = user_id

        return self.get(f"{self.BASE_PATH}/{food_item_id}/with-aliases", params=params)


    # Alias operations
    def create_food_item_alias(self, food_item_id: int, alias_data: dict[str, Any]) -> dict[str, Any]:
        """Create new alias for a food item."""
        return self.post(f"{self.BASE_PATH}/aliases/{food_item_id}/", alias_data)


    def get_aliases_for_food_item(self, food_item_id: int,
                                  user_id: int | None = None) -> list[dict[str, Any]]:
        """Get all aliases for a specific food item."""
        params: dict[str, Any] = {}
        if user_id:
            params['user_id'] = user_id

        return self.get(f"{self.BASE_PATH}/aliases/{food_item_id}/", params=params)


    def get_all_aliases_for_user(self, user_id: int,
                                 skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get all aliases created by a specific user."""
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        return self.get(f"{self.BASE_PATH}/aliases/users/{user_id}/", params=params)