"""Pydantic schemas for AI-related functionality."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from app.models.ai import OutputType, OutputFormat


class _AIModelOutputBase(BaseModel):
    """Base schema for AI model output validation."""

    user_id: int = Field(..., gt=0, description="ID of the user who initiated the AI request")
    model_version: str | None = Field(
        default=None,
        max_length=100,
        description="AI model version (e.g., 'gpt-4', 'claude-3')"
    )
    output_type: OutputType = Field(..., description="Type of AI output")
    output_format: OutputFormat | None = Field(
        default=None,
        description="Format of the output content"
    )
    prompt_used: str = Field(..., min_length=1, description="Input prompt sent to AI service")
    raw_output: str = Field(..., min_length=1, description="Raw output from AI service")
    extra_data: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata (tokens, cost, model info, etc.)"
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


class AIOutputSearchParams(BaseModel):
    """Schema for AI output search and filtering parameters."""

    user_id: int | None = Field(
        default=None,
        gt=0,
        description="Filter by user ID"
    )
    model_version: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by AI model version"
    )
    output_type: OutputType | None = Field(
        default=None,
        description="Filter by output type"
    )
    output_format: OutputFormat | None = Field(
        default=None,
        description="Filter by output format"
    )
    target_id: int | None = Field(
        default=None,
        gt=0,
        description="Filter by target entity ID"
    )
    prompt_contains: str | None = Field(
        default=None,
        min_length=1,
        description="Filter by text contained in prompt"
    )

    model_config = ConfigDict(from_attributes=True)


class AIOutputSummary(BaseModel):
    """Schema for AI output statistics summary."""

    total_outputs: int = Field(..., description="Total number of AI outputs")
    outputs_by_user: dict[str, int] = Field(..., description="Count by user ID")
    outputs_by_model: dict[str, int] = Field(..., description="Count by AI model")
    outputs_by_type: dict[str, int] = Field(..., description="Count by output type")
    outputs_by_format: dict[str, int] = Field(..., description="Count by output format")

    model_config = ConfigDict(from_attributes=True)