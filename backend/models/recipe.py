"""SQLAlchemy ORM models for recipes."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, JSON,
    Float, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.food import FoodItem
    from backend.models.core import Unit


class Recipe(Base):
    """Represents a row in the ``recipes`` table."""

    __tablename__ = "recipes"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuisine_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meal_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    created_by_user: Mapped[User | None] = relationship("User", back_populates="created_recipes")
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    steps: Mapped[list[RecipeStep]] = relationship(
        "RecipeStep", back_populates="recipe", cascade="all, delete-orphan",
        order_by="RecipeStep.step_number"
    )
    nutrition: Mapped[RecipeNutrition | None] = relationship(
        "RecipeNutrition", back_populates="recipe", uselist=False, cascade="all, delete-orphan"
    )
    reviews: Mapped[list[RecipeReview]] = relationship(
        "RecipeReview", back_populates="recipe", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"Recipe("
            f"id={self.id!r}, "
            f"title={self.title!r}, "
            f"difficulty={self.difficulty!r}, "
            f"servings={self.servings!r})"
        )


class RecipeIngredient(Base):
    """Represents a row in the ``recipe_ingredients`` table."""

    __tablename__ = "recipe_ingredients"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id"), primary_key=True, index=True
    )
    food_item_id: Mapped[int] = mapped_column(
        ForeignKey("food_items.id"), primary_key=True, index=True
    )
    amount_in_base_unit: Mapped[float] = mapped_column(Float, nullable=False)
    original_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id"), nullable=True
    )
    original_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")
    food_item: Mapped[FoodItem] = relationship("FoodItem")
    original_unit: Mapped[Unit | None] = relationship("Unit")

    # ------------------------------------------------------------------ #
    # Methods                                                             #
    # ------------------------------------------------------------------ #
    def display_amount(self) -> tuple[float, str]:
        """Return the display amount and unit for this ingredient."""
        if self.original_amount is not None and self.original_unit is not None:
            return self.original_amount, self.original_unit.name
        return self.amount_in_base_unit, self.food_item.base_unit.name

    def has_original_format(self) -> bool:
        """Check if this ingredient has original unit/amount information."""
        return (
                self.original_amount is not None
                and self.original_unit_id is not None
        )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"RecipeIngredient("
            f"recipe_id={self.recipe_id!r}, "
            f"food_item_id={self.food_item_id!r}, "
            f"amount_in_base_unit={self.amount_in_base_unit!r})"
        )


class RecipeStep(Base):
    """Represents a row in the ``recipe_steps`` table."""

    __tablename__ = "recipe_steps"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="steps")

    # ------------------------------------------------------------------ #
    # Constraints                                                         #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("recipe_id", "step_number", name="uq_recipe_step_number"),
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"RecipeStep("
            f"id={self.id!r}, "
            f"recipe_id={self.recipe_id!r}, "
            f"step_number={self.step_number!r})"
        )


class RecipeNutrition(Base):
    """Represents a row in the ``recipe_nutrition`` table."""

    __tablename__ = "recipe_nutrition"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id"), primary_key=True, index=True
    )
    kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="nutrition")

    # ------------------------------------------------------------------ #
    # Methods                                                             #
    # ------------------------------------------------------------------ #
    def has_complete_macros(self) -> bool:
        """Check if all macronutrients (protein, fat, carbs) are available."""
        return all(value is not None for value in [self.protein_g, self.fat_g, self.carbs_g])

    def calculated_kcal(self) -> float | None:
        """Calculate calories from macronutrients (4-4-9 rule)."""
        if not self.has_complete_macros():
            return None
        return (self.protein_g * 4) + (self.carbs_g * 4) + (self.fat_g * 9)

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"RecipeNutrition("
            f"recipe_id={self.recipe_id!r}, "
            f"kcal={self.kcal!r}, "
            f"source={self.source!r})"
        )


class RecipeReview(Base):
    """Represents a row in the ``recipe_reviews`` table."""

    __tablename__ = "recipe_reviews"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True, index=True
    )
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id"), primary_key=True, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    user: Mapped[User] = relationship("User")
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="reviews")

    # ------------------------------------------------------------------ #
    # Constraints                                                         #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("user_id", "recipe_id", name="uq_user_recipe_review"),
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"RecipeReview("
            f"user_id={self.user_id!r}, "
            f"recipe_id={self.recipe_id!r}, "
            f"rating={self.rating!r})"
        )
