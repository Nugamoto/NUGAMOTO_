"""Pydantic schemas for shopping system v2.0."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

from backend.core.enums import ShoppingListType


# ================================================================== #
# Shopping List Schemas                                              #
# ================================================================== #

class _ShoppingListBase(BaseModel):
    """Fields shared by all shopping list schemas."""

    name: str = Field(..., min_length=1, max_length=255)
    type: ShoppingListType

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate and normalize shopping list name."""
        if not v or v.isspace():
            raise ValueError("Shopping list name cannot be empty or whitespace")

        # Normalize to title case for consistency
        v = v.strip().title()

        if len(v) > 255:
            raise ValueError("Shopping list name must be 255 characters or less")

        return v


class ShoppingListCreate(_ShoppingListBase):
    """Schema for creating a new shopping list."""

    kitchen_id: int = Field(..., gt=0)


class ShoppingListRead(_ShoppingListBase):
    """Schema returned to the client."""

    id: int
    kitchen_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ShoppingListUpdate(BaseModel):
    """Schema for updating shopping list."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: ShoppingListType | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('name')
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and normalize shopping list name."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Shopping list name cannot be empty or whitespace")

        # Normalize to title case for consistency
        v = v.strip().title()

        if len(v) > 255:
            raise ValueError("Shopping list name must be 255 characters or less")

        return v


# ================================================================== #
# Shopping Product Schemas (v2.0)                                   #
# ================================================================== #

class _ShoppingProductBase(BaseModel):
    """Fields shared by all shopping product schemas."""

    food_item_id: int = Field(..., gt=0, description="Reference to food item")
    package_unit_id: int = Field(..., gt=0, description="Unit for the package")
    package_quantity: float = Field(
        ..., gt=0,
        description="Quantity per package in package_unit"
    )
    quantity_in_base_unit: float = Field(
        ..., gt=0,
        description="Equivalent quantity in food item's base unit"
    )
    package_type: str = Field(
        ..., min_length=1, max_length=100,
        description="Descriptive package type (e.g., '500 g pack')"
    )
    estimated_price: float | None = Field(
        default=None, ge=0,
        description="Estimated price for this package"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator("package_type")
    def validate_package_type(cls, v: str) -> str:
        """Validate and normalize package type."""
        if not v or v.isspace():
            raise ValueError("Package type cannot be empty or whitespace")

        # Keep original case but trim whitespace
        v = v.strip()

        if len(v) > 100:
            raise ValueError("Package type must be 100 characters or less")

        return v


class ShoppingProductCreate(_ShoppingProductBase):
    """Schema for creating a new shopping product."""
    pass


class ShoppingProductRead(_ShoppingProductBase):
    """Schema returned to the client."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Optional nested details
    food_item_name: str | None = Field(
        default=None,
        description="Name of the associated food item"
    )
    package_unit_name: str | None = Field(
        default=None,
        description="Name of the package unit"
    )
    base_unit_name: str | None = Field(
        default=None,
        description="Name of the food item's base unit"
    )
    unit_price: float | None = Field(
        default=None,
        description="Price per base unit if available"
    )


class ShoppingProductUpdate(BaseModel):
    """Schema for updating shopping product."""

    package_unit_id: int | None = Field(default=None, gt=0)
    package_quantity: float | None = Field(default=None, gt=0)
    quantity_in_base_unit: float | None = Field(default=None, gt=0)
    package_type: str | None = Field(default=None, min_length=1, max_length=100)
    estimated_price: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator("package_type")
    def validate_package_type(cls, v: str | None) -> str | None:
        """Validate and normalize package type."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Package type cannot be empty or whitespace")

        # Keep original case but trim whitespace
        v = v.strip()

        if len(v) > 100:
            raise ValueError("Package type must be 100 characters or less")

        return v


# ================================================================== #
# Shopping Product Assignment Schemas (v2.0)                        #
# ================================================================== #

class _ShoppingProductAssignmentBase(BaseModel):
    """Fields shared by assignment schemas."""

    added_by_user_id: int | None = Field(
        default=None, gt=0,
        description="User who added this item (None for system-generated)"
    )
    is_auto_added: bool = Field(
        default=False,
        description="True if added automatically by AI/system"
    )
    note: str | None = Field(
        default=None, max_length=500,
        description="User note about this specific assignment"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('note')
    def validate_note(cls, v: str | None) -> str | None:
        """Validate and normalize note field."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Note cannot be empty or whitespace")

        v = v.strip()

        if len(v) > 500:
            raise ValueError("Note must be 500 characters or less")

        return v


class ShoppingProductAssignmentCreate(_ShoppingProductAssignmentBase):
    """Schema for assigning a product to a list."""

    shopping_product_id: int = Field(..., gt=0)


class ShoppingProductAssignmentRead(_ShoppingProductAssignmentBase):
    """Schema returned to client with full product details."""

    shopping_list_id: int
    shopping_product_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Nested product details
    shopping_product: ShoppingProductRead


class ShoppingProductAssignmentUpdate(BaseModel):
    """Schema for updating assignment."""

    note: str | None = Field(
        default=None, max_length=500,
        description="Updated note for this assignment"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('note')
    def validate_note(cls, v: str | None) -> str | None:
        """Validate and normalize note field."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Note cannot be empty or whitespace")

        v = v.strip()

        if len(v) > 500:
            raise ValueError("Note must be 500 characters or less")

        return v


# ================================================================== #
# Search and Filter Parameters                                       #
# ================================================================== #

class ShoppingProductSearchParams(BaseModel):
    """Parameters for filtering shopping products."""

    food_item_id: int | None = Field(default=None, gt=0)
    package_unit_id: int | None = Field(default=None, gt=0)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    package_type: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)


class ShoppingProductAssignmentSearchParams(BaseModel):
    """Parameters for filtering product assignments."""

    is_auto_added: bool | None = None
    added_by_user_id: int | None = Field(default=None, gt=0)
    food_item_id: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Convenience Schemas                                                #
# ================================================================== #

class ShoppingListWithProducts(ShoppingListRead):
    """Shopping list with all assigned products."""

    product_assignments: list[ShoppingProductAssignmentRead] = Field(
        default_factory=list,
        description="All products assigned to this list"
    )
    total_products: int = Field(
        default=0,
        description="Total number of products on this list"
    )
    estimated_total: float | None = Field(
        default=None,
        description="Estimated total cost if prices are available"
    )


class ShoppingProductCreateWithAssignment(ShoppingProductCreate):
    """Create a product and immediately assign it to a list."""

    # Assignment fields
    added_by_user_id: int | None = Field(default=None, gt=0)
    is_auto_added: bool = Field(default=False)
    note: str | None = Field(default=None, max_length=500)


# ================================================================== #
# Unit Conversion Support (Future)                                   #
# ================================================================== #

class ShoppingProductCreateWithConversion(BaseModel):
    """Future schema for creating products with automatic unit conversion.
    
    This would allow users to input package details in any unit and
    automatically calculate the quantity_in_base_unit.
    """
    
    food_item_id: int = Field(..., gt=0)
    package_unit_id: int = Field(..., gt=0)
    package_quantity: float = Field(..., gt=0)
    # quantity_in_base_unit would be calculated automatically
    package_type: str = Field(..., min_length=1, max_length=100)
    estimated_price: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)