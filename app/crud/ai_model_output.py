"""CRUD operations for AI-related functionality v2.0 - Schema Returns."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AIOutputTargetType
from app.models.ai_model_output import AIModelOutput, OutputFormat, OutputType
from app.schemas.ai_model_output import (
    AIModelOutputCreate,
    AIModelOutputRead,
    AIOutputSearchParams,
    AIOutputSummary
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_ai_model_output_read(output_orm: AIModelOutput) -> AIModelOutputRead:
    """Convert AIModelOutput ORM to Read schema."""
    return AIModelOutputRead.model_validate(output_orm, from_attributes=True)


# ================================================================== #
# AI Model Output CRUD - Schema Returns                             #
# ================================================================== #

def create_ai_output(db: Session, output_data: AIModelOutputCreate) -> AIModelOutputRead:
    """Create a new AI model output record - returns schema.

    Args:
        db: Database session.
        output_data: Validated AI output data.

    Returns:
        The newly created AI model output schema.

    Example:
        >>> data = AIModelOutputCreate(
        ...     user_id=123,
        ...     model_version="gpt-4",
        ...     output_type=OutputType.RECIPE,
        ...     output_format=OutputFormat.MARKDOWN,
        ...     prompt_used="Generate a pasta recipe with tomatoes",
        ...     raw_output="# Tomato Pasta Recipe...",
        ...     target_type=AIOutputTargetType.RECIPE,
        ...     target_id=456,
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
        extra_data=output_data.extra_data,
        target_type=output_data.target_type,
        target_id=output_data.target_id,
    )

    db.add(db_output)
    db.commit()
    db.refresh(db_output)

    return build_ai_model_output_read(db_output)


def get_ai_output_by_id(db: Session, output_id: int) -> AIModelOutputRead | None:
    """Retrieve a single AI output by its ID - returns schema.

    Args:
        db: Database session.
        output_id: The unique identifier of the AI output.

    Returns:
        The AI output schema if found, None otherwise.

    Example:
        >>> output = get_ai_output_by_id(db, 123)
        >>> if output:
        ...     print(f"Found output for user: {output.user_id}")
        ...     print(f"Target: {output.target_type} (ID: {output.target_id})")
    """
    output_orm = get_ai_output_orm_by_id(db, output_id)

    if not output_orm:
        return None

    return build_ai_model_output_read(output_orm)


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
    output_orm = get_ai_output_orm_by_id(db, output_id)

    if output_orm is None:
        return False

    db.delete(output_orm)
    db.commit()
    return True


def get_all_ai_outputs(
        db: Session,
        search_params: AIOutputSearchParams,
        skip: int = 0,
        limit: int = 100
) -> list[AIModelOutputRead]:
    """Retrieve all AI outputs with optional filtering and pagination - returns schemas.

    Args:
        db: Database session.
        search_params: Search and filter parameters.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A list of AI output schemas matching the criteria, ordered by creation time (newest first).

    Example:
        >>> params = AIOutputSearchParams(
        ...     user_id=123,
        ...     output_type=OutputType.RECIPE,
        ...     target_type=AIOutputTargetType.RECIPE,
        ...     model_version="gpt-4"
        ... )
        >>> outputs = get_all_ai_outputs(db, params, skip=1, limit=5)
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

    if search_params.target_type:
        query = query.where(AIModelOutput.target_type == search_params.target_type)

    if search_params.target_id:
        query = query.where(AIModelOutput.target_id == search_params.target_id)

    if search_params.prompt_contains:
        query = query.where(AIModelOutput.prompt_used.ilike(f"%{search_params.prompt_contains}%"))

    # Order by creation time (newest first) and apply pagination
    query = query.order_by(AIModelOutput.created_at.desc()).offset(skip).limit(limit)

    outputs_list = db.scalars(query).all()
    return [build_ai_model_output_read(output) for output in outputs_list]


def get_ai_output_summary(db: Session) -> AIOutputSummary:
    """Get summary statistics for all AI outputs.

    Args:
        db: Database session.

    Returns:
        Summary statistics including counts by user, model, type, format, and target type.

    Example:
        >>> summary = get_ai_output_summary(db)
        >>> print(f"Total: {summary.total_outputs}")
        >>> print(f"Recipe outputs: {summary.outputs_by_target_type.get('Recipe', 0)}")
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

    # Count by target type
    target_type_counts = db.execute(
        select(AIModelOutput.target_type, func.count(AIModelOutput.id))
        .group_by(AIModelOutput.target_type)
    ).all()
    outputs_by_target_type = {str(target_type): count for target_type, count in target_type_counts}

    return AIOutputSummary(
        total_outputs=total_outputs,
        outputs_by_user=outputs_by_user,
        outputs_by_model=outputs_by_model,
        outputs_by_type=outputs_by_type,
        outputs_by_format=outputs_by_format,
        outputs_by_target_type=outputs_by_target_type,
    )


def get_ai_outputs_by_target(
        db: Session,
        target_type: AIOutputTargetType,
        target_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[AIModelOutputRead]:
    """Retrieve all AI outputs for a specific target entity - returns schemas.

    Args:
        db: Database session.
        target_type: Type of the target entity.
        target_id: ID of the target entity.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A list of AI output schemas for the specified target, ordered by creation time (newest first).

    Example:
        >>> outputs = get_ai_outputs_by_target(
        ...     db, AIOutputTargetType.RECIPE, 456, skip=1, limit=5
        ... )
        >>> print(f"Found {len(outputs)} AI outputs for recipe 456")
    """
    query = (
        select(AIModelOutput)
        .where(
            AIModelOutput.target_type == target_type,
            AIModelOutput.target_id == target_id
        )
        .order_by(AIModelOutput.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    outputs_list = db.scalars(query).all()
    return [build_ai_model_output_read(output) for output in outputs_list]


# ================================================================== #
# ORM Helper Functions (for internal use)                           #
# ================================================================== #

def get_ai_output_orm_by_id(db: Session, output_id: int) -> AIModelOutput | None:
    """Get AIModelOutput ORM object by ID - for internal use."""
    return db.scalar(select(AIModelOutput).where(AIModelOutput.id == output_id))
