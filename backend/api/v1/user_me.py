from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.dependencies import get_current_user
from backend.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
    operation_id="get_current_user_profile",
)
def get_me(current_user=Depends(get_current_user)) -> UserRead:
    """Return the current authenticated user's profile."""
    return current_user
