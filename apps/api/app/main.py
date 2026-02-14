from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_service import GeminiService, crisis_safe_response, has_self_harm_keywords
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import BuddyLink, BuddyLinkStatus, MoodCheckin, User
from app.schemas import (
    LadderRequest,
    LadderResult,
    LoginRequest,
    MoodCheckinCreate,
    MoodCheckinOut,
    RegisterRequest,
    SeedResponse,
    SeedUserCredentials,
    TokenResponse,
    TranslateRequest,
    TranslateResult,
    UserCreate,
    UserOut,
)
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


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@app.post("/ai/ladder", response_model=LadderResult)
def ai_ladder(
    payload: LadderRequest,
    _: User = Depends(get_current_user),
) -> LadderResult:
    try:
        service = GeminiService()
        return service.generate_ladder(payload.intake)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc}") from exc


@app.post("/ai/translate", response_model=TranslateResult)
def ai_translate(
    payload: TranslateRequest,
    _: User = Depends(get_current_user),
) -> TranslateResult:
    if has_self_harm_keywords(payload.message):
        return crisis_safe_response()

    try:
        service = GeminiService()
        result = service.translate_context(payload.message, payload.context)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc}") from exc

    if result.safety_flag == "crisis":
        return crisis_safe_response()
    return result


@app.post("/dev/seed", response_model=SeedResponse)
def seed_demo_users(db: Session = Depends(get_db)) -> SeedResponse:
    suffix = uuid.uuid4().hex[:8]
    center_lat = 38.9072
    center_lng = -77.0369
    offsets = [
        (0.0060, -0.0040),
        (-0.0050, 0.0030),
        (0.0040, 0.0050),
        (-0.0030, -0.0050),
        (0.0070, 0.0010),
        (-0.0060, -0.0020),
    ]

    primary_email = f"primary.{suffix}@komrade.local"
    primary_password = "DemoPass123!"
    primary_user = User(
        name="Primary Demo User",
        email=primary_email,
        hashed_password=hash_password(primary_password),
        lat=center_lat,
        lng=center_lng,
    )
    db.add(primary_user)
    db.flush()

    buddy_credentials: list[SeedUserCredentials] = []
    for i, (lat_offset, lng_offset) in enumerate(offsets, start=1):
        buddy_email = f"buddy{i}.{suffix}@komrade.local"
        buddy_password = f"BuddyPass{i}23!"
        buddy = User(
            name=f"Buddy {i}",
            email=buddy_email,
            hashed_password=hash_password(buddy_password),
            lat=center_lat + lat_offset,
            lng=center_lng + lng_offset,
        )
        db.add(buddy)
        db.flush()

        db.add(
            BuddyLink(
                user_id=primary_user.id,
                buddy_user_id=buddy.id,
                status=BuddyLinkStatus.accepted,
            )
        )
        buddy_credentials.append(
            SeedUserCredentials(email=buddy_email, password=buddy_password)
        )

    db.commit()
    return SeedResponse(
        primary_user=SeedUserCredentials(
            email=primary_email, password=primary_password
        ),
        buddy_users=buddy_credentials,
    )


@app.post("/dev/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> User:
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
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@app.post("/dev/mood_checkins", response_model=MoodCheckinOut, status_code=201)
def create_mood_checkin(
    payload: MoodCheckinCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> MoodCheckin:
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
    _: User = Depends(get_current_user),
) -> list[MoodCheckin]:
    query = select(MoodCheckin).order_by(MoodCheckin.created_at.desc())
    if user_id is not None:
        query = query.where(MoodCheckin.user_id == user_id)
    return list(db.scalars(query).all())
