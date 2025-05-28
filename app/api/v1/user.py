"""FastAPI router exposing the */users* endpoints."""

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.db.session import SessionLocal
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])

# --------------------------------------------------------------------- #
# Dependency                                                            #
# --------------------------------------------------------------------- #
def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------- #
# Routes                                                                #
# --------------------------------------------------------------------- #
@router.post("", response_model=UserRead, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if crud_user.get_user_by_email(db, str(user_in.email)):
        raise HTTPException(status_code=400, detail="Email already registered.")
    db_user = crud_user.create_user(db, user_in)
    return UserRead.model_validate(db_user, from_attributes=True)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get a user by ID",
)
def read_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    """Retrieve a single user by primary key.

    Args:
        user_id: Primary key of the user.
        db: Injected database session.

    Returns:
        The requested user.

    Raises:
        HTTPException: *404* if the user does not exist.
    """
    user = crud_user.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserRead.model_validate(user, from_attributes=True)
