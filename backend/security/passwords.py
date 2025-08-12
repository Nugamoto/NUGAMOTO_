from __future__ import annotations

from passlib.context import CryptContext


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for a given plain password.

    Args:
        plain_password: Raw user password.

    Returns:
        str: Bcrypt hash.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash.

    Args:
        plain_password: Raw user password.
        hashed_password: Stored bcrypt hash.

    Returns:
        bool: True if the password matches, otherwise False.
    """
    return _pwd_context.verify(plain_password, hashed_password)


def is_password_hashed(value: str | None) -> bool:
    """Heuristically check if a given value looks like a bcrypt hash.

    Args:
        value: String to test.

    Returns:
        bool: True if value seems to be an already hashed password.
    """
    if not value:
        return False
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")