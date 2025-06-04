"""Pydantic schemas for AI-related functionality."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

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


class AIOutputSearchParams(BaseModel):
    """Schema for AI output search and filtering parameters."""

    ai_service: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter by AI service"
    )
    output_type: Optional[OutputType] = Field(
        default=None,
        description="Filter by output type"
    )
    output_format: Optional[OutputFormat] = Field(
        default=None,
        description="Filter by output format"
    )
    target_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Filter by target entity ID"
    )
    prompt_contains: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Filter by text contained in prompt"
    )

    model_config = ConfigDict(from_attributes=True)


class AIOutputSummary(BaseModel):
    """Schema for AI output statistics summary."""

    total_outputs: int = Field(..., description="Total number of AI outputs")
    outputs_by_service: Dict[str, int] = Field(..., description="Count by AI service")
    outputs_by_type: Dict[str, int] = Field(..., description="Count by output type")
    outputs_by_format: Dict[str, int] = Field(..., description="Count by output format")

    model_config = ConfigDict(from_attributes=True)
