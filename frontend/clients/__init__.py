"""API clients for NUGAMOTO backend."""

from .auth_client import AuthClient
from .base import BaseClient, APIException
from .food_items_client import FoodItemsClient
from .inventory_items_client import InventoryItemsClient
from .kitchens_client import KitchensClient
from .storage_locations_client import StorageLocationsClient
from .units_client import UnitsClient
from .user_credentials_client import UserCredentialsClient
from .user_health_client import UserHealthClient
from .users_client import UsersClient

__all__ = [
    "BaseClient",
    "APIException",
    "FoodItemsClient",
    "InventoryItemsClient",
    "KitchensClient",
    "StorageLocationsClient",
    "UnitsClient",
    "UserCredentialsClient",
    "UserHealthClient",
    "UsersClient",
    "AuthClient",
]