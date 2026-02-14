from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MoodCheckin, User
from app.schemas import MoodCheckinCreate, MoodCheckinOut, UserCreate, UserOut
from app.settings import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/dev/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=payload.hashed_password,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/dev/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@app.post("/dev/mood_checkins", response_model=MoodCheckinOut, status_code=201)
def create_mood_checkin(payload: MoodCheckinCreate, db: Session = Depends(get_db)) -> MoodCheckin:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    checkin = MoodCheckin(
        user_id=payload.user_id,
        mood_score=payload.mood_score,
        note=payload.note,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@app.get("/dev/mood_checkins", response_model=list[MoodCheckinOut])
def list_mood_checkins(
    user_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MoodCheckin]:
    query = select(MoodCheckin).order_by(MoodCheckin.created_at.desc())
    if user_id is not None:
        query = query.where(MoodCheckin.user_id == user_id)
    return list(db.scalars(query).all())
