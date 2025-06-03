"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the request lifecycle.
    
    This dependency provides a database session that will be automatically
    closed after the request is completed, ensuring proper cleanup.
    
    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
