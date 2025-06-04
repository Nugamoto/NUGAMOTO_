"""SQLAlchemy ORM models for AI-related functionality."""

from __future__ import annotations

from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OutputType(str, Enum):
    """Enumeration of AI output types."""
    
    RECIPE = "recipe"
    NUTRITION_TIP = "nutrition_tip"
    SHOPPING_LIST = "shopping_list"
    MESSAGE = "message"


class OutputFormat(str, Enum):
    """Enumeration of AI output formats."""
    
    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class AIModelOutput(Base):
    """Represents a row in the ``ai_model_outputs`` table.

    Generic component for logging all AI-generated content including recipes,
    nutrition tips, messages, or shopping lists. Provides traceability and
    analytics capabilities for AI service usage.
    """

    __tablename__ = "ai_model_outputs"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ai_service: Mapped[str] = mapped_column(String(100), nullable=False)
    output_type: Mapped[OutputType] = mapped_column(nullable=False)
    output_format: Mapped[OutputFormat] = mapped_column(nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSON, default=None)
    target_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"AIModelOutput(id={self.id!r}, ai_service={self.ai_service!r}, "
            f"output_type={self.output_type!r})"
        )