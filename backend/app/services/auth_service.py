"""Auth service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get user by email."""
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def create_user(db: Session, data: RegisterRequest | UserCreate) -> User:
    """Create a new user."""
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=getattr(data, "role", "veteran"),
        latitude=getattr(data, "latitude", None),
        longitude=getattr(data, "longitude", None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate user by email and password."""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
