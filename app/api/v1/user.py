"""FastAPI router exposing the */users* endpoints."""

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.schemas.user import UserCreate, UserRead
from app.db.session import SessionLocal  # adjust import path if different

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
@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Create a new user.

    Args:
        user_in: Payload validated against :class:`~app.schemas.user.UserCreate`.
        db: Injected database session.

    Returns:
        The newly created user.

    Raises:
        HTTPException: *400* if the email is already registered.
    """
    if crud_user.get_user_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )
    return crud_user.create_user(db, user_in)


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user