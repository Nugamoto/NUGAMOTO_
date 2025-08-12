from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.crud import user as crud_user
from backend.crud import user_credentials as crud_user_credentials
from backend.schemas.auth import LoginRequest, TokenPair
from backend.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.security.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenPair, summary="Authenticate and issue tokens")
def login(
        payload: LoginRequest,
        db: Annotated[Session, Depends(get_db)],
) -> TokenPair:
    """Authenticate using email and password and return JWT tokens."""
    user_orm = crud_user.get_user_orm_by_email(db, email=payload.email)
    if not user_orm:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    creds_orm = crud_user_credentials.get_user_credentials_orm_by_user_id(db, user_id=user_orm.id)
    if not creds_orm or not creds_orm.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    stored_hash: str = cast(str, creds_orm.password_hash)
    if not verify_password(payload.password, stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    email_str: str = cast(str, user_orm.email)
    access = create_access_token(user_id=user_orm.id, extra_claims={"email": email_str})
    refresh = create_refresh_token(user_id=user_orm.id)

    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair, summary="Refresh access token")
def refresh(refresh_token: str) -> TokenPair:
    """Issue a new access token from a valid refresh token."""
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type")

    user_id = int(payload.get("sub"))
    access = create_access_token(user_id=user_id)
    new_refresh = create_refresh_token(user_id=user_id)

    return TokenPair(access_token=access, refresh_token=new_refresh)
