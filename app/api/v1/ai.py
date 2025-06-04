"""FastAPI router exposing the /ai endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import ai as crud_ai
from app.models.ai import OutputType, OutputFormat
from app.schemas.ai import (
    AIModelOutputCreate,
    AIModelOutputRead,
    AIOutputSearchParams,
    AIOutputSummary
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/outputs/",
    response_model=AIModelOutputRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new AI model output",
)
def create_ai_output(
        output_data: AIModelOutputCreate,
        db: Session = Depends(get_db)
) -> AIModelOutputRead:
    """Create a new AI model output record.

    This endpoint is used to log AI-generated content for tracking,
    analytics, and future reference. Supports all types of AI outputs
    including recipes, nutrition tips, coaching messages, shopping suggestions,
    and general content.

    Args:
        output_data: Validated AI output payload.
        db: Injected database session.

    Returns:
        The newly created AI output with timestamp and ID.

    Example:
        ```json
        {
            "user_id": 123,
            "model_version": "gpt-4",
            "output_type": "recipe",
            "output_format": "markdown",
            "prompt_used": "Generate a healthy pasta recipe",
            "raw_output": "# Healthy Veggie Pasta\\n\\n...",
            "extra_data": {
                "tokens": 250,
                "cost": 0.005,
                "temperature": 0.7
            },
            "target_id": 456
        }
        ```

    Note:
        This endpoint is primarily used by AI services internally,
        but can also be used for manual logging or testing purposes.
    """
    db_output = crud_ai.create_ai_output(db, output_data)
    return AIModelOutputRead.model_validate(db_output, from_attributes=True)


@router.get(
    "/outputs/{output_id}",
    response_model=AIModelOutputRead,
    status_code=status.HTTP_200_OK,
    summary="Get a specific AI output by ID",
)
def get_ai_output(
        output_id: int,
        db: Session = Depends(get_db),
) -> AIModelOutputRead:
    """Retrieve a specific AI output by its unique identifier.

    Args:
        output_id: The unique identifier of the AI output.
        db: Injected database session.

    Returns:
        The requested AI output.

    Raises:
        HTTPException: 404 if the AI output is not found.

    Example:
        ```
        GET /ai/outputs/123
        ```

    Note:
        This endpoint is useful for examining specific AI outputs,
        debugging, or integrating AI outputs into other systems.
    """
    db_output = crud_ai.get_ai_output_by_id(db, output_id)

    if db_output is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI output with ID {output_id} not found"
        )

    return AIModelOutputRead.model_validate(db_output, from_attributes=True)


@router.delete(
    "/outputs/{output_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific AI output",
)
def delete_ai_output(
        output_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete a specific AI output by its unique identifier.

    Args:
        output_id: The unique identifier of the AI output to delete.
        db: Injected database session.

    Raises:
        HTTPException: 404 if the AI output is not found.

    Example:
        ```
        DELETE /ai/outputs/123
        ```

    Note:
        This operation is irreversible. Use with caution.
        Typically used for cleanup, privacy compliance (GDPR), 
        or removing test/invalid data.
    """
    success = crud_ai.delete_ai_output(db, output_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI output with ID {output_id} not found"
        )


@router.get(
    "/outputs/",
    response_model=list[AIModelOutputRead],
    status_code=status.HTTP_200_OK,
    summary="Get all AI outputs with optional filtering",
)
def get_all_ai_outputs(
        user_id: int | None = Query(None, gt=0, description="Filter by user ID"),
        model_version: str | None = Query(None, description="Filter by AI model version"),
        output_type: OutputType | None = Query(None, description="Filter by output type"),
        output_format: OutputFormat | None = Query(None, description="Filter by output format"),
        target_id: int | None = Query(None, gt=0, description="Filter by target entity ID"),
        prompt_contains: str | None = Query(None, description="Filter by text in prompt"),
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        db: Session = Depends(get_db),
) -> list[AIModelOutputRead]:
    """Retrieve all AI outputs with optional search and filtering.

    Supports pagination and various filter criteria. Results are ordered
    by creation time (newest first) for better usability.

    Args:
        user_id: Optional filter for specific user.
        model_version: Optional filter for AI model version (gpt-4, claude-3, etc.).
        output_type: Optional filter for output type (recipe, nutrition_tip, etc.).
        output_format: Optional filter for output format (json, markdown, plain_text).
        target_id: Optional filter for linked entity ID.
        prompt_contains: Optional text search within prompts (case-insensitive).
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.
        db: Injected database session.

    Returns:
        A list of AI outputs matching the criteria.

    Example:
        ```
        GET /ai/outputs/?user_id=123&output_type=recipe&model_version=gpt-4&limit=20
        ```

    Note:
        This endpoint is useful for analytics, debugging AI outputs,
        and building AI output management interfaces.
    """
    search_params = AIOutputSearchParams(
        user_id=user_id,
        model_version=model_version,
        output_type=output_type,
        output_format=output_format,
        target_id=target_id,
        prompt_contains=prompt_contains,
    )

    outputs = crud_ai.get_all_ai_outputs(db, search_params, skip, limit)
    return [AIModelOutputRead.model_validate(output, from_attributes=True) for output in outputs]


@router.get(
    "/outputs/summary",
    response_model=AIOutputSummary,
    status_code=status.HTTP_200_OK,
    summary="Get AI output statistics summary",
)
def get_ai_output_summary(db: Session = Depends(get_db)) -> AIOutputSummary:
    """Retrieve summary statistics for all AI outputs.

    Provides overview statistics including total counts and breakdowns
    by user, AI model, output type, and format. Useful for analytics dashboards.

    Args:
        db: Injected database session.

    Returns:
        Summary statistics with counts grouped by various dimensions.

    Example Response:
        ```json
        {
            "total_outputs": 1250,
            "outputs_by_user": {
                "123": 400,
                "456": 350,
                "789": 500
            },
            "outputs_by_model": {
                "gpt-4": 800,
                "claude-3": 450
            },
            "outputs_by_type": {
                "recipe": 600,
                "nutrition_tip": 400,
                "coaching_message": 150,
                "general": 100
            },
            "outputs_by_format": {
                "markdown": 700,
                "json": 400,
                "plain_text": 150
            }
        }
        ```

    Note:
        This endpoint is particularly useful for monitoring AI usage patterns,
        user behavior analysis, and making decisions about AI service allocation.
    """
    return crud_ai.get_ai_output_summary(db)