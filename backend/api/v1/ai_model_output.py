"""FastAPI router exposing the ai endpoints."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db, get_current_user_id, require_super_admin
from backend.core.enums import AIOutputTargetType
from backend.crud import ai_model_output as crud_ai
from backend.models.ai_model_output import OutputType, OutputFormat
from backend.schemas.ai_model_output import (
    AIModelOutputCreate,
    AIModelOutputRead,
    AIOutputSearchParams,
    AIOutputSummary
)
from backend.security import decode_token

router = APIRouter(prefix="/ai", tags=["AI Outputs"])

_auth_scheme = HTTPBearer()


def _is_admin(credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
    """Return True if token has admin-like claims."""
    if not credentials:
        return False
    try:
        payload = decode_token(credentials.credentials)
        is_superadmin = bool(payload.get("is_superadmin"))
        is_admin = bool(payload.get("is_admin"))
        role = str(payload.get("role", "") or "").lower()
        perms = payload.get("permissions") or []
        if isinstance(perms, str):
            perms = [perms]
        by_role = role in {"superadmin", "admin"}
        by_perm = "users:create" in {str(p).lower() for p in perms}
        return is_superadmin or is_admin or by_role or by_perm
    except Exception:
        return False


@router.post(
    "/outputs/",
    response_model=AIModelOutputRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new AI model output",
    dependencies=[Depends(get_current_user_id)],
)
def create_ai_output(
        output_data: AIModelOutputCreate,
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
) -> AIModelOutputRead:
    """Create a new AI model output record.

    Security:
        - Auth required
        - Self-only: output_data.user_id must equal current user
    """
    if output_data.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create AI outputs for another user",
        )

    return crud_ai.create_ai_output(db, output_data)


@router.get(
    "/outputs/{output_id}",
    response_model=AIModelOutputRead,
    status_code=status.HTTP_200_OK,
    summary="Get a specific AI output by ID",
    dependencies=[Depends(get_current_user_id)],
)
def get_ai_output(
        output_id: int,
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_auth_scheme)] = None,
) -> AIModelOutputRead:
    """Retrieve a specific AI output by its unique identifier.

    Security:
        - Auth required
        - Owner-only unless admin
    """
    db_output = crud_ai.get_ai_output_by_id(db, output_id)

    if db_output is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI output with ID {output_id} not found"
        )

    if db_output.user_id != current_user_id and not _is_admin(credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this resource",
        )

    return db_output


@router.delete(
    "/outputs/{output_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific AI output",
    response_class=Response,
    dependencies=[Depends(require_super_admin)],
)
def delete_ai_output(
        output_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a specific AI output by its unique identifier.

    Security:
        - Admin-only
    """
    success = crud_ai.delete_ai_output(db, output_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI output with ID {output_id} not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/outputs/",
    response_model=list[AIModelOutputRead],
    status_code=status.HTTP_200_OK,
    summary="Get all AI outputs with optional filtering",
    dependencies=[Depends(get_current_user_id)],
)
def get_all_ai_outputs(
        user_id: int | None = Query(None, gt=0, description="Filter by user ID"),
        model_version: str | None = Query(None, description="Filter by AI model version"),
        output_type: OutputType | None = Query(None, description="Filter by output type"),
        output_format: OutputFormat | None = Query(None, description="Filter by output format"),
        target_type: AIOutputTargetType | None = Query(None, description="Filter by target entity type"),
        target_id: int | None = Query(None, gt=0, description="Filter by target entity ID"),
        prompt_contains: str | None = Query(None, description="Filter by text in prompt"),
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_auth_scheme)] = None,
) -> list[AIModelOutputRead]:
    """Retrieve all AI outputs with optional search and filtering.

    Security:
        - Auth required
        - Non-admins can only see their own outputs (user_id is forced to current user)
        - Admins can query any user_id or all users
    """
    effective_user_id = user_id
    if not _is_admin(credentials):
        effective_user_id = current_user_id  # force self-only view

    search_params = AIOutputSearchParams(
        user_id=effective_user_id,
        model_version=model_version,
        output_type=output_type,
        output_format=output_format,
        target_type=target_type,
        target_id=target_id,
        prompt_contains=prompt_contains,
    )

    return crud_ai.get_all_ai_outputs(db, search_params, skip, limit)


@router.get(
    "/outputs/targets/{target_type}/{target_id}",
    response_model=list[AIModelOutputRead],
    status_code=status.HTTP_200_OK,
    summary="Get all AI outputs for a specific target entity",
    dependencies=[Depends(get_current_user_id)],
)
def get_ai_outputs_by_target(
        target_type: AIOutputTargetType,
        target_id: int,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_auth_scheme)] = None,
) -> list[AIModelOutputRead]:
    """Retrieve all AI outputs associated with a specific target entity.

    Security:
        - Auth required
        - Non-admins only receive outputs belonging to themselves
        - Admins receive all outputs for the target
    """
    outputs = crud_ai.get_ai_outputs_by_target(db, target_type, target_id, skip, limit)

    if _is_admin(credentials):
        return outputs

    # Filter to current user only for non-admins
    return [o for o in outputs if getattr(o, "user_id", None) == current_user_id]


@router.get(
    "/outputs/summary",
    response_model=AIOutputSummary,
    status_code=status.HTTP_200_OK,
    summary="Get AI output statistics summary",
    dependencies=[Depends(require_super_admin)],
)
def get_ai_output_summary(db: Session = Depends(get_db)) -> AIOutputSummary:
    """Retrieve summary statistics for all AI outputs.

    Security:
        - Admin-only
    """
    return crud_ai.get_ai_output_summary(db)