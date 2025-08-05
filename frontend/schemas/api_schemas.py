"""Schema imports from NUGAMOTO backend."""

import os
import sys
from typing import TYPE_CHECKING

# Add backend to Python path
BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, BACKEND_PATH)

# Import backend schemas
if TYPE_CHECKING:
    from backend.schemas.core import UnitCreate, UnitRead, UnitUpdate
    from backend.schemas.food import FoodItemCreate, FoodItemRead, FoodItemUpdate
else:
    try:
        from backend.schemas.core import UnitCreate, UnitRead, UnitUpdate
        from backend.schemas.food import FoodItemCreate, FoodItemRead, FoodItemUpdate
    except ImportError as e:
        raise ImportError(f"Failed to import backend schemas: {e}") from e

__all__ = [
    "UnitCreate",
    "UnitRead", 
    "UnitUpdate",
    "FoodItemCreate",
    "FoodItemRead",
    "FoodItemUpdate",
]