"""CRUD operations for AI-related functionality."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai import AIModelOutput, OutputFormat, OutputType
from app.schemas.ai import AIModelOutputCreate, AIOutputSearchParams, AIOutputSummary


def create_ai_output(db: Session, output_data: AIModelOutputCreate) -> AIModelOutput:
    """Create a new AI model output record.

    Args:
        db: Database session.
        output_data: Validated AI output data.

    Returns:
        The newly created AI model output.

    Example:
        >>> data = AIModelOutputCreate(
        ...     user_id=123,
        ...     model_version="gpt-4",
        ...     output_type=OutputType.RECIPE,
        ...     output_format=OutputFormat.MARKDOWN,
        ...     prompt_used="Generate a pasta recipe with tomatoes",
        ...     raw_output="# Tomato Pasta Recipe...",
        ...     extra_data={"tokens": 150, "cost": 0.003}
        ... )
        >>> result = create_ai_output(db, data)
    """
    db_output = AIModelOutput(
        user_id=output_data.user_id,
        model_version=output_data.model_version,
        output_type=output_data.output_type,
        output_format=output_data.output_format,
        prompt_used=output_data.prompt_used,
        raw_output=output_data.raw_output,
        extra_data=output_data.extra_data,  # ← GEÄNDERT!
        target_id=output_data.target_id,
    )

    db.add(db_output)
    db.commit()
    db.refresh(db_output)

    return db_output


def get_ai_output_by_id(db: Session, output_id: int) -> AIModelOutput | None:
    """Retrieve a single AI output by its ID.

    Args:
        db: Database session.
        output_id: The unique identifier of the AI output.

    Returns:
        The AI output if found, None otherwise.

    Example:
        >>> output = get_ai_output_by_id(db, 123)
        >>> if output:
        ...     print(f"Found output for user: {output.user_id}")
    """
    return db.scalar(select(AIModelOutput).where(AIModelOutput.id == output_id))


def delete_ai_output(db: Session, output_id: int) -> bool:
    """Delete an AI output by its ID.

    Args:
        db: Database session.
        output_id: The unique identifier of the AI output to delete.

    Returns:
        True if the output was deleted, False if it wasn't found.

    Example:
        >>> success = delete_ai_output(db, 123)
        >>> if success:
        ...     print("Output deleted successfully")
    """
    output = db.scalar(select(AIModelOutput).where(AIModelOutput.id == output_id))

    if output is None:
        return False

    db.delete(output)
    db.commit()
    return True


def get_all_ai_outputs(
        db: Session,
        search_params: AIOutputSearchParams,
        skip: int = 0,
        limit: int = 100
) -> list[AIModelOutput]:
    """Retrieve all AI outputs with optional filtering and pagination.

    Args:
        db: Database session.
        search_params: Search and filter parameters.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A list of AI outputs matching the criteria, ordered by creation time (newest first).

    Example:
        >>> params = AIOutputSearchParams(
        ...     user_id=123,
        ...     output_type=OutputType.RECIPE,
        ...     model_version="gpt-4"
        ... )
        >>> outputs = get_all_ai_outputs(db, params, skip=0, limit=10)
    """
    query = select(AIModelOutput)

    # Apply filters
    if search_params.user_id:
        query = query.where(AIModelOutput.user_id == search_params.user_id)

    if search_params.model_version:
        query = query.where(AIModelOutput.model_version == search_params.model_version)

    if search_params.output_type:
        query = query.where(AIModelOutput.output_type == search_params.output_type)

    if search_params.output_format:
        query = query.where(AIModelOutput.output_format == search_params.output_format)

    if search_params.target_id:
        query = query.where(AIModelOutput.target_id == search_params.target_id)

    if search_params.prompt_contains:
        query = query.where(AIModelOutput.prompt_used.ilike(f"%{search_params.prompt_contains}%"))

    # Order by creation time (newest first) and apply pagination
    query = query.order_by(AIModelOutput.created_at.desc()).offset(skip).limit(limit)

    return list(db.scalars(query).all())


def get_ai_output_summary(db: Session) -> AIOutputSummary:
    """Get summary statistics for all AI outputs.

    Args:
        db: Database session.

    Returns:
        Summary statistics including counts by user, model, type, and format.

    Example:
        >>> summary = get_ai_output_summary(db)
        >>> print(f"Total: {summary.total_outputs}")
    """
    # Total count
    total_outputs = db.scalar(select(func.count(AIModelOutput.id))) or 0

    # Count by user
    user_counts = db.execute(
        select(AIModelOutput.user_id, func.count(AIModelOutput.id))
        .group_by(AIModelOutput.user_id)
    ).all()
    outputs_by_user = {str(user_id): count for user_id, count in user_counts}

    # Count by model version
    model_counts = db.execute(
        select(AIModelOutput.model_version, func.count(AIModelOutput.id))
        .group_by(AIModelOutput.model_version)
    ).all()
    outputs_by_model = {str(model or "unknown"): count for model, count in model_counts}

    # Count by output type
    type_counts = db.execute(
        select(AIModelOutput.output_type, func.count(AIModelOutput.id))
        .group_by(AIModelOutput.output_type)
    ).all()
    outputs_by_type = {str(output_type): count for output_type, count in type_counts}

    # Count by output format
    format_counts = db.execute(
        select(AIModelOutput.output_format, func.count(AIModelOutput.id))
        .group_by(AIModelOutput.output_format)
    ).all()
    outputs_by_format = {str(output_format or "unknown"): count for output_format, count in format_counts}

    return AIOutputSummary(
        total_outputs=total_outputs,
        outputs_by_user=outputs_by_user,
        outputs_by_model=outputs_by_model,
        outputs_by_type=outputs_by_type,
        outputs_by_format=outputs_by_format,
    )