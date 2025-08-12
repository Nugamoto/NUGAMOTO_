from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db, get_current_user_id
from backend.schemas.user import UserRead
from backend.crud import user as crud_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead, summary="Get current user profile")
def get_me(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
) -> UserRead:
    """Return the current authenticated user's profile."""
    me = crud_user.get_user_by_id(db, current_user_id)
    if not me:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return me