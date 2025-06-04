"""Pydantic schemas for AI-related functionality."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict

from app.models.ai import OutputType, OutputFormat


class _AIModelOutputBase(BaseModel):
    """Base schema for AI model output validation."""

    ai_service: str = Field(..., min_length=1, max_length=100, description="AI service identifier")
    output_type: OutputType = Field(..., description="Type of AI output")
    output_format: OutputFormat = Field(..., description="Format of the output content")
    prompt: str = Field(..., min_length=1, description="Input prompt sent to AI service")
    content: str = Field(..., min_length=1, description="Generated content from AI service")
    metadata: Dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata (tokens, cost, model version, etc.)"
    )
    target_id: int | None = Field(
        default=None,
        gt=0,
        description="Optional ID linking to related entity (recipe, user, etc.)"
    )

    model_config = ConfigDict(from_attributes=True)


class AIModelOutputCreate(_AIModelOutputBase):
    """Schema for creating new AI model outputs."""
    pass


class AIModelOutputRead(_AIModelOutputBase):
    """Schema for reading AI model outputs."""

    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")