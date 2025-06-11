"""SQLAlchemy ORM models for user credentials and authentication data."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserCredentials(Base):
    """Stores authentication credentials and personal metadata separate from core user profile."""

    __tablename__ = "user_credentials"

    # ------------------------------------------------------------------ #
    # Columns                                                            #
    # ------------------------------------------------------------------ #
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Reference to the user this credentials belong to"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password for authentication"
    )
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User's first name"
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User's last name"
    )
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User's street address"
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User's city"
    )
    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="User's postal/ZIP code"
    )
    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User's country"
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="User's phone number"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp when credentials were created"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp of last credentials update"
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                      #
    # ------------------------------------------------------------------ #
    user: Mapped[User] = relationship("User", back_populates="credentials")

    # ------------------------------------------------------------------ #
    # Properties                                                         #
    # ------------------------------------------------------------------ #
    @property
    def full_name(self) -> str | None:
        """Get formatted full name from first and last name.

        Returns:
            Combined full name if both parts available, single part if only one exists, None otherwise.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name

    @property
    def full_address(self) -> str | None:
        """Get formatted full address from address components.

        Returns:
            Multi-line formatted address string or None if no address components exist.
        """
        components = []

        if self.address:
            components.append(self.address)

        city_line = " ".join(filter(None, [self.postal_code, self.city]))
        if city_line:
            components.append(city_line)

        if self.country:
            components.append(self.country)

        return "\n".join(components) if components else None

    def __repr__(self) -> str:
        return f"UserCredentials(user_id={self.user_id!r}, full_name={self.full_name!r})"