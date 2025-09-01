from __future__ import annotations

import os
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from passlib.exc import MissingBackendError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.crud import user as crud_user
from backend.crud import user_credentials as crud_user_credentials
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from backend.schemas.user import UserCreate
from backend.schemas.user_credentials import UserCredentialsCreate
from backend.security import create_access_token, create_refresh_token, decode_token
from backend.security.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


def _parse_csv_env(name: str) -> set[str]:
    """Parse a comma-separated env var to a lower-cased set (trimmed)."""
    raw = os.getenv(name, "") or ""
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def _is_admin_email(email: str) -> bool:
    """Return True if the email should get admin privileges based on whitelist.

    Supported env variables:
      - ADMIN_EMAILS: comma-separated exact email matches
      - ADMIN_EMAIL_DOMAINS: comma-separated domains (e.g., example.com)
    """
    email_l = (email or "").strip().lower()
    allowed_emails = _parse_csv_env("ADMIN_EMAILS")
    allowed_domains = _parse_csv_env("ADMIN_EMAIL_DOMAINS")

    if email_l in allowed_emails:
        return True

    if "@" in email_l:
        domain = email_l.split("@", 1)[1]
        if domain in allowed_domains:
            return True

    return False


def _admin_claims_for_email(email: str) -> dict:
    """Build admin claims if email qualifies, otherwise empty dict."""
    if _is_admin_email(email):
        # Flexible set of claims recognized by require_super_admin
        return {
            "is_admin": True,
            "role": "admin",
            "permissions": ["users:create"],
        }
    return {}


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
def register(
        payload: RegisterRequest,
        db: Annotated[Session, Depends(get_db)],
) -> TokenPair:
    """Register a new user and return token pair (auto-login)."""
    # 1) Check uniqueness by email
    existing = crud_user.get_user_orm_by_email(db, email=payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 2) Create user (returns a schema)
    user = crud_user.create_user(
        db=db,
        user_data=UserCreate(name=payload.name, email=payload.email, diet_type=None, allergies=None, preferences=None),
    )

    try:
        # 3) Create credentials (hashing handled in the CRUD)
        cred_in = UserCredentialsCreate(
            password_hash=payload.password,
            first_name=None,
            last_name=None,
            address=None,
            city=None,
            postal_code=None,
            country=None,
            phone=None,
        )
        crud_user_credentials.create_user_credentials(
            db=db, user_id=user.id, credentials_data=cred_in
        )

    except MissingBackendError:
        # bcrypt backend not installed; cleanup user ORM and return a clear error
        user_orm = crud_user.get_user_orm_by_email(db, email=payload.email)
        if user_orm:
            db.delete(user_orm)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password hashing backend not available. Please install 'bcrypt' and restart the service.",
        )

    except Exception as exc:
        # Any other failure during credential creation -> cleanup newly created user (ORM)
        user_orm = crud_user.get_user_orm_by_email(db, email=payload.email)
        if user_orm:
            try:
                db.delete(user_orm)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later.",
        ) from exc

    # 4) Issue token pair (auto-login) with optional admin claims based on whitelist
    email_str = cast(str, user.email)
    base_claims = {"email": email_str}
    claims = {**base_claims, **_admin_claims_for_email(email_str)}

    access = create_access_token(user_id=user.id, extra_claims=claims)
    refresh = create_refresh_token(user_id=user.id)
    return TokenPair(access_token=access, refresh_token=refresh, token_type="bearer")


@router.post("/login", response_model=TokenPair, summary="Authenticate and issue tokens")
def login(
        payload: LoginRequest,
        db: Annotated[Session, Depends(get_db)],
) -> TokenPair:
    """Authenticate using email and password and return JWT tokens."""
    user_orm = crud_user.get_user_orm_by_email(db, email=payload.email)
    if not user_orm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    creds_orm = crud_user_credentials.get_user_credentials_orm_by_user_id(
        db, user_id=user_orm.id
    )
    if not creds_orm or not creds_orm.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    stored_hash: str = cast(str, creds_orm.password_hash)
    if not verify_password(payload.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Access token with admin claims based on whitelist
    email_str = cast(str, user_orm.email)
    base_claims = {"email": email_str}
    claims = {**base_claims, **_admin_claims_for_email(email_str)}

    access = create_access_token(user_id=user_orm.id, extra_claims=claims)
    refresh = create_refresh_token(user_id=user_orm.id)

    return TokenPair(access_token=access, refresh_token=refresh, token_type="bearer")


@router.post("/refresh", response_model=TokenPair, summary="Refresh access token")
def refresh(
        refresh_token: str,
        db: Annotated[Session, Depends(get_db)],
) -> TokenPair:
    """Issue a new access token from a valid refresh token.

    Recomputes admin claims via whitelist to retain permissions on refresh.
    """
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type"
        )

    user_id = int(payload.get("sub"))

    # Recompute admin claims based on user's current email
    user_orm = crud_user.get_user_orm_by_email(
        db, email=cast(str, crud_user.get_user_by_id(db, user_id).email)
    ) if crud_user.get_user_by_id(db, user_id) else None

    if not user_orm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    email_str = cast(str, user_orm.email)
    base_claims = {"email": email_str}
    claims = {**base_claims, **_admin_claims_for_email(email_str)}

    access = create_access_token(user_id=user_id, extra_claims=claims)
    new_refresh = create_refresh_token(user_id=user_id)

    return TokenPair(access_token=access, refresh_token=new_refresh, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout (stateless)")
def logout() -> Response:
    """Stateless logout. Client must delete stored tokens."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)