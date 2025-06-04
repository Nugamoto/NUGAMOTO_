"""FastAPI router exposing the /ai endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import ai as crud_ai
from app.schemas.ai import AIModelOutputCreate, AIModelOutputRead

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
    including recipes, nutrition tips, messages, and shopping lists.

    Args:
        output_data: Validated AI output payload.
        db: Injected database session.

    Returns:
        The newly created AI output with timestamp and ID.

    Example:
        ```json
        {
            "ai_service": "openai-gpt4",
            "output_type": "recipe",
            "output_format": "markdown",
            "prompt": "Generate a healthy pasta recipe",
            "content": "# Healthy Veggie Pasta\\n\\n...",
            "metadata": {
                "tokens": 250,
                "cost": 0.005,
                "model_version": "gpt-4-0125-preview"
            },
            "target_id": 123
        }
        ```

    Note:
        This endpoint is primarily used by AI services internally,
        but can also be used for manual logging or testing purposes.
    """
    db_output = crud_ai.create_ai_output(db, output_data)
    return AIModelOutputRead.model_validate(db_output, from_attributes=True)