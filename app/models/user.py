"""SQLAlchemy ORM model for application users."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base


class User(Base):
    """Represents a row in the ``users`` table."""

    __tablename__ = "users"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    diet_type: Mapped[Optional[str]] = mapped_column(String(50))
    allergies: Mapped[Optional[str]] = mapped_column(Text)
    preferences: Mapped[Optional[str]] = mapped_column(Text)

    # ------------------------------------------------------------------ #
    # Validators                                                          #
    # ------------------------------------------------------------------ #
    @validates("email")
    def _validate_email(self, _key: str, address: str) -> str:
        """Lower-case and perform a minimal email sanity check.

        Args:
            _key: The column key being validated (unused).
            address: Raw email address.

        Returns:
            Sanitised email address.

        Raises:
            ValueError: If the address does not look like an email.
        """
        if "@" not in address:
            raise ValueError("Invalid email address")
        return address.lower()

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            "User("
            f"id={self.id!r}, "
            f"name={self.name!r}, "
            f"email={self.email!r}, "
            f"diet_type={self.diet_type!r})"
        )