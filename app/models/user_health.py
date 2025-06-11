"""SQLAlchemy ORM models for user health profiles."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserHealthProfile(Base):
    """Represents a user's health profile for personalized recommendations.

    This model stores personal health data including physical attributes,
    activity levels, health conditions, and personal goals for AI-driven
    nutrition and fitness recommendations.
    """

    __tablename__ = "user_health_profiles"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Reference to the user this profile belongs to"
    )
    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="User's age in years"
    )
    gender: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="User's gender (e.g., 'male', 'female', 'non-binary', 'prefer not to say')"
    )
    height_cm: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="User's height in centimeters"
    )
    weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="User's weight in kilograms"
    )
    activity_level: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Activity level (e.g., 'sedentary', 'lightly active', 'moderately active', 'very active', 'extremely active')"
    )
    health_conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User's health conditions and medical notes"
    )
    goal: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="User's health/fitness goals (e.g., 'lose weight', 'gain muscle', 'maintain health')"
    )
    last_updated: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp of last profile update"
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    user: Mapped[User] = relationship("User", back_populates="health_profile")

    # ------------------------------------------------------------------ #
    # Properties                                                          #
    # ------------------------------------------------------------------ #
    @property
    def bmi(self) -> float | None:
        """Calculate Body Mass Index if height and weight are available.

        Returns:
            BMI value (weight_kg / (height_m)^2) or None if data is incomplete.
        """
        if self.height_cm is None or self.weight_kg is None:
            return None
        if self.height_cm <= 0 or self.weight_kg <= 0:
            return None
        height_m = self.height_cm / 100.0
        return self.weight_kg / (height_m ** 2)

    @property
    def is_complete(self) -> bool:
        """Check if the profile has all essential data for recommendations.

        Returns:
            True if age, gender, height, weight, and activity level are set.
        """
        return all([
            self.age is not None,
            self.gender is not None,
            self.height_cm is not None,
            self.weight_kg is not None,
            self.activity_level is not None
        ])

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"UserHealthProfile(id={self.id!r}, user_id={self.user_id!r}, "
            f"age={self.age!r}, gender={self.gender!r}, "
            f"height_cm={self.height_cm!r}, weight_kg={self.weight_kg!r})"
        )