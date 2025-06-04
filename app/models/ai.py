"""SQLAlchemy ORM models for AI-related functionality."""

from __future__ import annotations

from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OutputType(str, Enum):
    """Enumeration of AI output types."""
    
    RECIPE = "recipe"
    NUTRITION_TIP = "nutrition_tip"
    SHOPPING_LIST = "shopping_list"
    COACHING_MESSAGE = "coaching_message"
    SHOPPING_SUGGESTION = "shopping_suggestion"
    GENERAL = "general"  # For anything that doesn't fit other categories


class OutputFormat(str, Enum):
    """Enumeration of AI output formats."""
    
    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class AIModelOutput(Base):
    """Represents a row in the ``ai_model_outputs`` table.

    Generic component for logging all AI-generated content including recipes,
    nutrition tips, coaching messages, shopping suggestions, and general content.
    Provides traceability and analytics capabilities for AI service usage.
    """

    __tablename__ = "ai_model_outputs"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    model_version: Mapped[str | None] = mapped_column(String(100), default=None)
    output_type: Mapped[OutputType] = mapped_column(nullable=False)
    output_format: Mapped[OutputFormat | None] = mapped_column(default=None)
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    raw_output: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    target_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"AIModelOutput(id={self.id!r}, user_id={self.user_id!r}, "
            f"output_type={self.output_type!r})"
        )