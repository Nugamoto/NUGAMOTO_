"""Schema imports from NUGAMOTO backend."""

import os
import sys

# Add backend to Python path
BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, BACKEND_PATH)

# Direct imports without TYPE_CHECKING block
from backend.schemas.core import UnitCreate, UnitRead, UnitUpdate
from backend.schemas.food import FoodItemCreate, FoodItemRead, FoodItemUpdate

__all__ = [
    "UnitCreate",
    "UnitRead", 
    "UnitUpdate",
    "FoodItemCreate",
    "FoodItemRead",
    "FoodItemUpdate",
]