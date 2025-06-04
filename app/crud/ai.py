"""CRUD operations for AI-related functionality."""

from sqlalchemy.orm import Session

from app.models.ai import AIModelOutput
from app.schemas.ai import AIModelOutputCreate


def create_ai_output(db: Session, output_data: AIModelOutputCreate) -> AIModelOutput:
    """Create a new AI model output record.

    Args:
        db: Database session.
        output_data: Validated AI output data.

    Returns:
        The newly created AI model output.

    Example:
        >>> output_data = AIModelOutputCreate(
        ...     ai_service="openai-gpt4",
        ...     output_type=OutputType.RECIPE,
        ...     output_format=OutputFormat.MARKDOWN,
        ...     prompt="Generate a pasta recipe with tomatoes",
        ...     content="# Tomato Pasta Recipe...",
        ...     metadata={"tokens": 150, "cost": 0.003}
        ... )
        >>> result = create_ai_output(db, output_data)
    """
    db_output = AIModelOutput(
        ai_service=output_data.ai_service,
        output_type=output_data.output_type,
        output_format=output_data.output_format,
        prompt=output_data.prompt,
        content=output_data.content,
        metadata=output_data.metadata,
        target_id=output_data.target_id,
    )

    db.add(db_output)
    db.commit()
    db.refresh(db_output)

    return db_output