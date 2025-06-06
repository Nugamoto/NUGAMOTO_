"""SQLAlchemy ORM models for recipe system v2.0."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, Text, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.inventory import FoodItem, Unit


class Recipe(Base):
    """Represents a row in the ``recipes`` table.

    Recipes contain multiple ingredients and steps, with optional nutrition data.
    """

    __tablename__ = "recipes"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    created_by_user: Mapped[User | None] = relationship("User")
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    steps: Mapped[list[RecipeStep]] = relationship(
        "RecipeStep", back_populates="recipe", cascade="all, delete-orphan"
    )
    nutrition: Mapped[RecipeNutrition | None] = relationship(
        "RecipeNutrition", back_populates="recipe", cascade="all, delete-orphan"
    )
    reviews: Mapped[list[RecipeReview]] = relationship(
        "RecipeReview", back_populates="recipe", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"Recipe(id={self.id!r}, title={self.title!r}, "
            f"is_ai_generated={self.is_ai_generated!r})"
        )


class RecipeIngredient(Base):
    """Represents a row in the ``recipe_ingredients`` table (v2.0).

    Links recipes to food items with amounts stored in base units.
    Optionally preserves the original unit and amount for display purposes.
    Uses a composite primary key of recipe_id and food_item_id.
    """

    __tablename__ = "recipe_ingredients"

    # ------------------------------------------------------------------ #
    # Columns (Composite Primary Key)                                    #
    # ------------------------------------------------------------------ #
    recipe_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    food_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("food_items.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )

    # ------------------------------------------------------------------ #
    # Required Fields                                                     #
    # ------------------------------------------------------------------ #
    amount_in_base_unit: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Amount in the food item's base unit (e.g., grams)"
    )

    # ------------------------------------------------------------------ #
    # Optional Original Input Fields                                      #
    # ------------------------------------------------------------------ #
    original_unit_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("units.id"),
        nullable=True,
        index=True,
        comment="Unit as originally entered by user (e.g., 'tsp', 'cup')"
    )
    original_amount: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Amount as originally entered by user (e.g., 0.5, 1, 3)"
    )

    # ------------------------------------------------------------------ #
    # Timestamps                                                          #
    # ------------------------------------------------------------------ #
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    last_updated: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")
    food_item: Mapped[FoodItem] = relationship("FoodItem")
    original_unit: Mapped[Unit | None] = relationship("Unit", foreign_keys=[original_unit_id])

    # ------------------------------------------------------------------ #
    # Properties                                                          #
    # ------------------------------------------------------------------ #
    @property
    def display_amount(self) -> float:
        """Get the amount to display (original or base unit).
        
        Returns:
            Original amount if available, otherwise base unit amount.
        """
        return self.original_amount if self.original_amount is not None else self.amount_in_base_unit

    @property
    def has_original_format(self) -> bool:
        """Check if original unit/amount information is available.
        
        Returns:
            True if both original_unit_id and original_amount are set.
        """
        return self.original_unit_id is not None and self.original_amount is not None

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"RecipeIngredient(recipe_id={self.recipe_id!r}, "
            f"food_item_id={self.food_item_id!r}, "
            f"amount_in_base_unit={self.amount_in_base_unit!r})"
        )


class RecipeStep(Base):
    """Represents a row in the ``recipe_steps`` table.

    Contains the ordered cooking instructions for a recipe.
    """

    __tablename__ = "recipe_steps"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="steps")

    # ------------------------------------------------------------------ #
    # Table Constraints                                                   #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Ensure unique step numbers per recipe
        {"schema": None}  # Placeholder for unique constraint
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"RecipeStep(recipe_id={self.recipe_id!r}, "
            f"step_number={self.step_number!r})"
        )


class RecipeNutrition(Base):
    """Represents a row in the ``recipe_nutrition`` table.

    Contains nutritional information for a recipe.
    """

    __tablename__ = "recipe_nutrition"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    recipe_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="nutrition")

    # ------------------------------------------------------------------ #
    # Properties                                                          #
    # ------------------------------------------------------------------ #
    @property
    def has_complete_macros(self) -> bool:
        """Check if all macro nutrients are available.
        
        Returns:
            True if protein, fat, and carbs are all non-None.
        """
        return all(x is not None for x in [self.protein_g, self.fat_g, self.carbs_g])

    @property
    def calculated_kcal(self) -> float | None:
        """Calculate calories from macronutrients.
        
        Uses standard conversion: 4 kcal/g for protein and carbs, 9 kcal/g for fat.
        
        Returns:
            Calculated calories or None if macros are incomplete.
        """
        if not self.has_complete_macros:
            return None

        protein_kcal = self.protein_g * 4
        fat_kcal = self.fat_g * 9
        carbs_kcal = self.carbs_g * 4

        return protein_kcal + fat_kcal + carbs_kcal

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"RecipeNutrition(recipe_id={self.recipe_id!r}, "
            f"kcal={self.kcal!r})"
        )


class RecipeReview(Base):
    """Represents a row in the ``recipe_reviews`` table.

    User reviews and ratings for recipes.
    """

    __tablename__ = "recipe_reviews"

    # ------------------------------------------------------------------ #
    # Columns (Composite Primary Key)                                    #
    # ------------------------------------------------------------------ #
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    recipe_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )

    # ------------------------------------------------------------------ #
    # Review Data                                                         #
    # ------------------------------------------------------------------ #
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    user: Mapped[User] = relationship("User")
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="reviews")

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"RecipeReview(user_id={self.user_id!r}, "
            f"recipe_id={self.recipe_id!r}, rating={self.rating!r})"
        )