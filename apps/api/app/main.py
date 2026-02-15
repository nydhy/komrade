from __future__ import annotations

import asyncio
import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.ai_service import GeminiService, crisis_safe_response, has_self_harm_keywords
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import (
    Alert,
    BuddyPresence,
    BuddyLink,
    BuddyLinkStatus,
    Checkin,
    LadderChallenge,
    LadderPlan,
    Report,
    MoodCheckin,
    SosAlert,
    SosRecipient,
    User,
    UserSettings,
)
from app.schemas import (
    BuddyInviteRequest,
    BuddyLinkResponse,
    BuddyLinkWithUser,
    IncomingSosAlertResponse,
    LadderChallengeCompleteRequest,
    LadderChallengeOut,
    LadderPlanCreateRequest,
    LadderPlanOut,
    LadderRequest,
    LadderResult,
    LegacyMoodCheckinCreate,
    LegacyMoodCheckinResponse,
    LoginRequest,
    LocationUpdate,
    MoodCheckinCreate,
    MoodCheckinOut,
    NearbyBuddyResponse,
    PresenceResponse,
    PresenceUpdate,
    ReportCreate,
    RegisterRequest,
    SeedResponse,
    SeedUserCredentials,
    SosAlertResponse,
    SosFromCheckinCreate,
    SosManualCreate,
    SosRecipientResponse,
    SosRespondRequest,
    TokenResponse,
    TranslateRequest,
    TranslateResult,
    UpdateProfileRequest,
    UserCreate,
    UserMe,
    UserOut,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.settings import settings

app = FastAPI(title=settings.app_name)

default_origins = {"http://localhost:3000", "http://localhost:5173"}
default_origins.add(settings.web_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(default_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WsManager:
    def __init__(self) -> None:
        self.active: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[user_id].add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        self.active.get(user_id, set()).discard(websocket)
        if not self.active.get(user_id):
            self.active.pop(user_id, None)

    async def send_to_user(self, user_id: uuid.UUID, event: str, data: dict) -> None:
        payload = {"event": event, "data": data}
        for ws in list(self.active.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)

    async def send_to_users(self, user_ids: list[uuid.UUID], event: str, data: dict) -> None:
        await asyncio.gather(
            *[self.send_to_user(user_id, event, data) for user_id in set(user_ids)],
            return_exceptions=True,
        )


ws_manager = WsManager()


def _user_to_me(user: User) -> UserMe:
    return UserMe(
        id=user.id,
        email=user.email,
        full_name=user.name,
        role=user.role,
        is_active=user.is_active,
        latitude=float(user.lat) if user.lat is not None else None,
        longitude=float(user.lng) if user.lng is not None else None,
        created_at=user.created_at,
    )


def _upper_link_status(status: str) -> str:
    if status.lower() == "accepted":
        return "ACCEPTED"
    if status.lower() == "pending":
        return "PENDING"
    return status.upper()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return r * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _get_or_create_settings(db: Session, user_id: uuid.UUID) -> UserSettings:
    settings_row = db.scalar(select(UserSettings).where(UserSettings.user_id == user_id))
    if settings_row is None:
        settings_row = UserSettings(user_id=user_id, share_precise_location=True, sos_radius_km=50.0)
        db.add(settings_row)
        db.flush()
    return settings_row


def _schedule_ws(coro: Any) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        pass


def _enrich_sos_alert(db: Session, alert: SosAlert) -> SosAlertResponse:
    recipients_rows = list(
        db.scalars(select(SosRecipient).where(SosRecipient.sos_alert_id == alert.id)).all()
    )
    recipients: list[SosRecipientResponse] = []
    for rec in recipients_rows:
        buddy = db.get(User, rec.buddy_id)
        recipients.append(
            SosRecipientResponse(
                id=rec.id,
                sos_alert_id=rec.sos_alert_id,
                buddy_id=rec.buddy_id,
                status=rec.status,
                message=rec.message,
                eta_minutes=rec.eta_minutes,
                responded_at=rec.responded_at,
                buddy_email=buddy.email if buddy else "",
                buddy_name=buddy.name if buddy else "",
            )
        )
    return SosAlertResponse(
        id=alert.id,
        veteran_id=alert.veteran_id,
        trigger_type=alert.trigger_type,
        severity=alert.severity,
        status=alert.status,
        created_at=alert.created_at,
        closed_at=alert.closed_at,
        recipients=recipients,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserMe, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserMe:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already exists")

    full_name = (payload.full_name or payload.name or "").strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="name/full_name is required")

    user = User(
        name=full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role.lower(),
        lat=payload.latitude,
        lng=payload.longitude,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_me(user)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@app.get("/auth/me", response_model=UserMe)
def auth_me(current_user: User = Depends(get_current_user)) -> UserMe:
    return _user_to_me(current_user)


@app.put("/auth/me", response_model=UserMe)
def update_auth_me(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserMe:
    if payload.full_name is not None and payload.full_name.strip():
        current_user.name = payload.full_name.strip()
    if payload.latitude is not None:
        current_user.lat = payload.latitude
    if payload.longitude is not None:
        current_user.lng = payload.longitude
    db.commit()
    db.refresh(current_user)
    return _user_to_me(current_user)


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


@app.post("/buddies/invite", response_model=BuddyLinkResponse)
def invite_buddy(
    payload: BuddyInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuddyLinkResponse:
    if payload.buddy_email is None and payload.buddy_id is None:
        raise HTTPException(status_code=400, detail="Provide buddy_email or buddy_id")
    buddy = None
    if payload.buddy_email:
        buddy = db.scalar(select(User).where(User.email == payload.buddy_email.lower().strip()))
    elif payload.buddy_id:
        buddy = db.get(User, payload.buddy_id)
    if buddy is None:
        raise HTTPException(status_code=404, detail="Buddy not found")
    if buddy.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    existing = db.scalar(
        select(BuddyLink).where(
            or_(
                (BuddyLink.user_id == current_user.id) & (BuddyLink.buddy_user_id == buddy.id),
                (BuddyLink.user_id == buddy.id) & (BuddyLink.buddy_user_id == current_user.id),
            )
        )
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Buddy link already exists")

    link = BuddyLink(
        user_id=current_user.id,
        buddy_user_id=buddy.id,
        status=BuddyLinkStatus.pending,
        trust_level=payload.trust_level,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return BuddyLinkResponse(
        id=link.id,
        veteran_id=link.user_id,
        buddy_id=link.buddy_user_id,
        status=_upper_link_status(link.status.value if hasattr(link.status, "value") else str(link.status)),
        trust_level=link.trust_level,
        created_at=link.created_at,
    )


@app.post("/buddies/{link_id}/accept", response_model=BuddyLinkResponse)
def accept_buddy_invite(
    link_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuddyLinkResponse:
    link = db.get(BuddyLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Buddy link not found")
    if link.buddy_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only invited buddy can accept")
    link.status = BuddyLinkStatus.accepted
    db.commit()
    return BuddyLinkResponse(
        id=link.id,
        veteran_id=link.user_id,
        buddy_id=link.buddy_user_id,
        status="ACCEPTED",
        trust_level=link.trust_level,
        created_at=link.created_at,
    )


@app.post("/buddies/{link_id}/block", response_model=BuddyLinkResponse)
def block_buddy_link(
    link_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuddyLinkResponse:
    link = db.get(BuddyLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Buddy link not found")
    if current_user.id not in {link.user_id, link.buddy_user_id}:
        raise HTTPException(status_code=403, detail="Not your buddy link")
    link.status = BuddyLinkStatus.pending
    db.commit()
    return BuddyLinkResponse(
        id=link.id,
        veteran_id=link.user_id,
        buddy_id=link.buddy_user_id,
        status="BLOCKED",
        trust_level=link.trust_level,
        created_at=link.created_at,
    )


@app.get("/buddies", response_model=list[BuddyLinkWithUser])
def list_buddies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BuddyLinkWithUser]:
    links = list(
        db.scalars(
            select(BuddyLink).where(
                or_(BuddyLink.user_id == current_user.id, BuddyLink.buddy_user_id == current_user.id)
            )
        ).all()
    )
    result: list[BuddyLinkWithUser] = []
    for link in links:
        other_id = link.buddy_user_id if link.user_id == current_user.id else link.user_id
        other = db.get(User, other_id)
        presence = db.scalar(select(BuddyPresence).where(BuddyPresence.user_id == other_id))
        status_value = link.status.value if hasattr(link.status, "value") else str(link.status)
        result.append(
            BuddyLinkWithUser(
                id=link.id,
                veteran_id=link.user_id,
                buddy_id=link.buddy_user_id,
                status=_upper_link_status(status_value),
                trust_level=link.trust_level,
                created_at=link.created_at,
                other_email=other.email if other else "",
                other_name=other.name if other else "",
                other_latitude=float(other.lat) if other and other.lat is not None else None,
                other_longitude=float(other.lng) if other and other.lng is not None else None,
                other_presence_status=presence.status if presence else "OFFLINE",
            )
        )
    return result


@app.post("/checkins", response_model=LegacyMoodCheckinResponse)
def create_checkin(
    payload: LegacyMoodCheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyMoodCheckinResponse:
    checkin = MoodCheckin(
        user_id=current_user.id,
        mood_score=payload.mood_score,
        tags=payload.tags,
        note=payload.note,
        wants_company=payload.wants_company,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return LegacyMoodCheckinResponse(
        id=checkin.id,
        veteran_id=checkin.user_id,
        mood_score=checkin.mood_score,
        tags=checkin.tags or [],
        note=checkin.note,
        wants_company=checkin.wants_company,
        created_at=checkin.created_at,
    )


@app.get("/checkins/me", response_model=list[LegacyMoodCheckinResponse])
def get_my_checkins(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LegacyMoodCheckinResponse]:
    rows = list(
        db.scalars(
            select(MoodCheckin)
            .where(MoodCheckin.user_id == current_user.id)
            .order_by(desc(MoodCheckin.created_at), desc(MoodCheckin.id))
            .limit(limit)
        ).all()
    )
    return [
        LegacyMoodCheckinResponse(
            id=row.id,
            veteran_id=row.user_id,
            mood_score=row.mood_score,
            tags=row.tags or [],
            note=row.note,
            wants_company=row.wants_company,
            created_at=row.created_at,
        )
        for row in rows
    ]


@app.get("/presence/me", response_model=PresenceResponse)
def get_presence_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PresenceResponse:
    presence = db.scalar(select(BuddyPresence).where(BuddyPresence.user_id == current_user.id))
    if presence is None:
        return PresenceResponse(user_id=current_user.id, status="OFFLINE", updated_at=datetime.now(timezone.utc))
    return PresenceResponse(user_id=presence.user_id, status=presence.status, updated_at=presence.updated_at)


@app.post("/presence", response_model=PresenceResponse)
def update_presence(
    payload: PresenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PresenceResponse:
    presence = db.scalar(select(BuddyPresence).where(BuddyPresence.user_id == current_user.id))
    if presence is None:
        presence = BuddyPresence(user_id=current_user.id, status=payload.status)
        db.add(presence)
    else:
        presence.status = payload.status
        presence.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(presence)
    return PresenceResponse(user_id=presence.user_id, status=presence.status, updated_at=presence.updated_at)


@app.post("/location")
def update_location(
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Union[float, str]]:
    current_user.lat = payload.latitude
    current_user.lng = payload.longitude
    db.commit()
    return {"status": "ok", "latitude": payload.latitude, "longitude": payload.longitude}


@app.get("/buddies/nearby", response_model=list[NearbyBuddyResponse])
def get_nearby_buddies(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NearbyBuddyResponse]:
    links = list(
        db.scalars(
            select(BuddyLink).where(
                BuddyLink.user_id == current_user.id,
                BuddyLink.status == BuddyLinkStatus.accepted,
            )
        ).all()
    )
    rows: list[NearbyBuddyResponse] = []
    for link in links:
        buddy = db.get(User, link.buddy_user_id)
        if buddy is None:
            continue
        presence = db.scalar(select(BuddyPresence).where(BuddyPresence.user_id == buddy.id))
        distance = None
        if current_user.lat is not None and current_user.lng is not None and buddy.lat is not None and buddy.lng is not None:
            distance = _haversine_km(float(current_user.lat), float(current_user.lng), float(buddy.lat), float(buddy.lng))
        rows.append(
            NearbyBuddyResponse(
                buddy_id=buddy.id,
                buddy_name=buddy.name,
                buddy_email=buddy.email,
                trust_level=link.trust_level,
                presence_status=presence.status if presence else "OFFLINE",
                distance_km=distance,
            )
        )
    rows.sort(key=lambda item: (item.presence_status != "AVAILABLE", -item.trust_level, item.distance_km or 10**9))
    return rows[:limit]


@app.get("/settings/me", response_model=UserSettingsResponse)
def get_my_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = _get_or_create_settings(db, current_user.id)
    db.commit()
    return UserSettingsResponse(
        user_id=row.user_id,
        quiet_hours_start=row.quiet_hours_start,
        quiet_hours_end=row.quiet_hours_end,
        share_precise_location=row.share_precise_location,
        sos_radius_km=row.sos_radius_km,
        updated_at=row.updated_at,
    )


@app.put("/settings/me", response_model=UserSettingsResponse)
def update_my_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = _get_or_create_settings(db, current_user.id)
    if payload.quiet_hours_start is not None:
        row.quiet_hours_start = payload.quiet_hours_start
    if payload.quiet_hours_end is not None:
        row.quiet_hours_end = payload.quiet_hours_end
    if payload.share_precise_location is not None:
        row.share_precise_location = payload.share_precise_location
    if payload.sos_radius_km is not None:
        row.sos_radius_km = payload.sos_radius_km
    db.commit()
    db.refresh(row)
    return UserSettingsResponse(
        user_id=row.user_id,
        quiet_hours_start=row.quiet_hours_start,
        quiet_hours_end=row.quiet_hours_end,
        share_precise_location=row.share_precise_location,
        sos_radius_km=row.sos_radius_km,
        updated_at=row.updated_at,
    )


@app.post("/report", status_code=201)
def report_user(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if payload.reported_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot report yourself")
    reported = db.get(User, payload.reported_user_id)
    if reported is None:
        raise HTTPException(status_code=404, detail="User not found")
    row = Report(
        reporter_id=current_user.id,
        reported_user_id=payload.reported_user_id,
        reason=payload.reason,
    )
    db.add(row)
    db.commit()
    return {"status": "reported", "report_id": str(row.id)}


def _select_sos_buddy_ids(
    db: Session, veteran_id: uuid.UUID, buddy_ids: Optional[List[uuid.UUID]], broadcast: bool
) -> list[uuid.UUID]:
    accepted_links = list(
        db.scalars(
            select(BuddyLink).where(
                BuddyLink.user_id == veteran_id,
                BuddyLink.status == BuddyLinkStatus.accepted,
            )
        ).all()
    )
    accepted_ids = [link.buddy_user_id for link in accepted_links]
    if not accepted_ids:
        raise HTTPException(status_code=400, detail="No accepted buddies available")
    if broadcast:
        return accepted_ids[:5]
    if buddy_ids:
        filtered = [buddy_id for buddy_id in buddy_ids if buddy_id in accepted_ids]
        if filtered:
            return filtered
    return accepted_ids[:5]


@app.get("/sos/me", response_model=list[SosAlertResponse])
def sos_me(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SosAlertResponse]:
    alerts = list(
        db.scalars(
            select(SosAlert)
            .where(SosAlert.veteran_id == current_user.id)
            .order_by(desc(SosAlert.created_at), desc(SosAlert.id))
            .limit(limit)
        ).all()
    )
    return [_enrich_sos_alert(db, alert) for alert in alerts]


@app.post("/sos", response_model=SosAlertResponse)
def create_manual_sos(
    payload: SosManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SosAlertResponse:
    selected = _select_sos_buddy_ids(db, current_user.id, payload.buddy_ids, payload.broadcast)
    alert = SosAlert(veteran_id=current_user.id, trigger_type="MANUAL", severity=payload.severity, status="OPEN")
    db.add(alert)
    db.flush()
    for buddy_id in selected:
        db.add(SosRecipient(sos_alert_id=alert.id, buddy_id=buddy_id, status="NOTIFIED"))
    db.commit()
    enriched = _enrich_sos_alert(db, alert)
    _schedule_ws(ws_manager.send_to_users(selected, "sos.created", enriched.model_dump(mode="json")))
    return enriched


@app.post("/sos/from-checkin/{checkin_id}", response_model=SosAlertResponse)
def create_sos_from_checkin(
    checkin_id: uuid.UUID,
    payload: SosFromCheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SosAlertResponse:
    checkin = db.get(MoodCheckin, checkin_id)
    if checkin is None or checkin.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Check-in not found")
    selected = _select_sos_buddy_ids(db, current_user.id, payload.buddy_ids, payload.broadcast)
    alert = SosAlert(veteran_id=current_user.id, trigger_type="MOOD", severity=payload.severity, status="OPEN")
    db.add(alert)
    db.flush()
    for buddy_id in selected:
        db.add(SosRecipient(sos_alert_id=alert.id, buddy_id=buddy_id, status="NOTIFIED"))
    db.commit()
    enriched = _enrich_sos_alert(db, alert)
    _schedule_ws(ws_manager.send_to_users(selected, "sos.created", enriched.model_dump(mode="json")))
    return enriched


@app.get("/sos/incoming", response_model=list[IncomingSosAlertResponse])
def get_incoming_sos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IncomingSosAlertResponse]:
    recipients = list(
        db.scalars(select(SosRecipient).where(SosRecipient.buddy_id == current_user.id)).all()
    )
    result: list[IncomingSosAlertResponse] = []
    for rec in recipients:
        alert = db.get(SosAlert, rec.sos_alert_id)
        if alert is None:
            continue
        veteran = db.get(User, alert.veteran_id)
        result.append(
            IncomingSosAlertResponse(
                alert_id=alert.id,
                veteran_id=alert.veteran_id,
                veteran_name=veteran.name if veteran else "",
                trigger_type=alert.trigger_type,
                severity=alert.severity,
                alert_status=alert.status,
                created_at=alert.created_at,
                recipient_id=rec.id,
                my_status=rec.status,
                my_message=rec.message,
                my_eta_minutes=rec.eta_minutes,
                responded_at=rec.responded_at,
            )
        )
    result.sort(key=lambda r: r.created_at, reverse=True)
    return result


@app.get("/sos/{sos_id}", response_model=SosAlertResponse)
def get_sos(
    sos_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SosAlertResponse:
    alert = db.get(SosAlert, sos_id)
    if alert is None or alert.veteran_id != current_user.id:
        raise HTTPException(status_code=404, detail="SOS not found")
    return _enrich_sos_alert(db, alert)


@app.post("/sos/{sos_id}/close", response_model=SosAlertResponse)
def close_sos(
    sos_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SosAlertResponse:
    alert = db.get(SosAlert, sos_id)
    if alert is None or alert.veteran_id != current_user.id:
        raise HTTPException(status_code=404, detail="SOS not found")
    alert.status = "CLOSED"
    alert.closed_at = datetime.now(timezone.utc)
    db.commit()
    enriched = _enrich_sos_alert(db, alert)
    notify_ids = [r.buddy_id for r in enriched.recipients] + [current_user.id]
    _schedule_ws(
        ws_manager.send_to_users(notify_ids, "sos.closed", {"sos_id": str(sos_id), "status": "CLOSED"})
    )
    return enriched


@app.post("/sos/{sos_id}/escalate", response_model=SosAlertResponse)
def escalate_sos(
    sos_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SosAlertResponse:
    alert = db.get(SosAlert, sos_id)
    if alert is None or alert.veteran_id != current_user.id:
        raise HTTPException(status_code=404, detail="SOS not found")
    if alert.status == "CLOSED":
        raise HTTPException(status_code=400, detail="SOS is closed")
    already = {
        rec.buddy_id for rec in db.scalars(select(SosRecipient).where(SosRecipient.sos_alert_id == alert.id)).all()
    }
    extra_candidates = list(
        db.scalars(
            select(BuddyLink).where(
                BuddyLink.user_id == current_user.id,
                BuddyLink.status == BuddyLinkStatus.accepted,
            )
        ).all()
    )
    new_ids: list[uuid.UUID] = []
    for link in extra_candidates:
        if link.buddy_user_id not in already:
            db.add(SosRecipient(sos_alert_id=alert.id, buddy_id=link.buddy_user_id, status="NOTIFIED"))
            new_ids.append(link.buddy_user_id)
            if len(new_ids) >= 3:
                break
    if not new_ids:
        raise HTTPException(status_code=400, detail="No additional buddies to escalate")
    alert.status = "ESCALATED"
    db.commit()
    enriched = _enrich_sos_alert(db, alert)
    _schedule_ws(ws_manager.send_to_users(new_ids, "sos.created", enriched.model_dump(mode="json")))
    return enriched


@app.post("/sos/{sos_id}/respond", response_model=SosRecipientResponse)
def respond_to_sos(
    sos_id: uuid.UUID,
    payload: SosRespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SosRecipientResponse:
    rec = db.scalar(
        select(SosRecipient).where(
            SosRecipient.sos_alert_id == sos_id,
            SosRecipient.buddy_id == current_user.id,
        )
    )
    if rec is None:
        raise HTTPException(status_code=403, detail="You are not a recipient for this SOS")
    rec.status = payload.status
    rec.message = payload.message
    rec.eta_minutes = payload.eta_minutes
    rec.responded_at = datetime.now(timezone.utc)
    db.commit()
    buddy = db.get(User, rec.buddy_id)
    alert = db.get(SosAlert, sos_id)
    if alert:
        _schedule_ws(
            ws_manager.send_to_user(
                alert.veteran_id,
                "sos.recipient_updated",
                {
                    "sos_id": str(sos_id),
                    "recipient_id": str(rec.id),
                    "buddy_id": str(rec.buddy_id),
                    "buddy_name": buddy.name if buddy else "",
                    "status": rec.status,
                    "message": rec.message,
                    "eta_minutes": rec.eta_minutes,
                },
            )
        )
    return SosRecipientResponse(
        id=rec.id,
        sos_alert_id=rec.sos_alert_id,
        buddy_id=rec.buddy_id,
        status=rec.status,
        message=rec.message,
        eta_minutes=rec.eta_minutes,
        responded_at=rec.responded_at,
        buddy_email=buddy.email if buddy else "",
        buddy_name=buddy.name if buddy else "",
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        user_id = uuid.UUID(str(sub))
    except (JWTError, ValueError):
        await websocket.close(code=4003, reason="Invalid token")
        return

    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user_id, websocket)


@app.post("/ladder/plans", response_model=LadderPlanOut, status_code=201)
def create_ladder_plan(
    payload: LadderPlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LadderPlanOut:
    plan_json = {"weeks": [week.model_dump() for week in payload.weeks]}
    plan = LadderPlan(user_id=current_user.id, plan_json=plan_json)
    db.add(plan)
    db.flush()

    challenges: list[LadderChallenge] = []
    for week in payload.weeks:
        challenge = LadderChallenge(
            plan_id=plan.id,
            week=week.week,
            title=week.title,
            difficulty=week.difficulty,
            suggested_time=week.suggested_time,
            status="pending",
        )
        db.add(challenge)
        challenges.append(challenge)
    db.flush()
    db.commit()
    db.refresh(plan)

    return LadderPlanOut(
        plan_id=plan.id,
        created_at=plan.created_at,
        challenges=[
            LadderChallengeOut(
                id=challenge.id,
                week=challenge.week,
                title=challenge.title,
                difficulty=challenge.difficulty,
                rationale=payload.weeks[index].rationale,
                suggested_time=challenge.suggested_time,
                status=challenge.status,
                completed=False,
            )
            for index, challenge in enumerate(challenges)
        ],
    )


@app.get("/ladder/plans/latest", response_model=LadderPlanOut)
def latest_ladder_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LadderPlanOut:
    plan = db.scalar(
        select(LadderPlan)
        .where(LadderPlan.user_id == current_user.id)
        .order_by(LadderPlan.created_at.desc())
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No ladder plan found")

    challenges = list(
        db.scalars(
            select(LadderChallenge)
            .where(LadderChallenge.plan_id == plan.id)
            .order_by(LadderChallenge.week.asc())
        ).all()
    )
    checkins_by_challenge: dict[uuid.UUID, bool] = {
        challenge_id: True
        for challenge_id in db.scalars(
            select(Checkin.challenge_id).where(Checkin.challenge_id.in_([c.id for c in challenges]))
        ).all()
    }

    rationale_by_week: dict[int, str] = {}
    for item in plan.plan_json.get("weeks", []):
        if isinstance(item, dict) and "week" in item:
            rationale_by_week[int(item["week"])] = str(item.get("rationale", ""))

    return LadderPlanOut(
        plan_id=plan.id,
        created_at=plan.created_at,
        challenges=[
            LadderChallengeOut(
                id=challenge.id,
                week=challenge.week,
                title=challenge.title,
                difficulty=challenge.difficulty,
                rationale=rationale_by_week.get(challenge.week, ""),
                suggested_time=challenge.suggested_time,
                status=challenge.status,
                completed=checkins_by_challenge.get(challenge.id, False),
            )
            for challenge in challenges
        ],
    )


@app.post("/ladder/challenges/{challenge_id}/complete", response_model=LadderPlanOut)
def complete_ladder_challenge(
    challenge_id: uuid.UUID,
    payload: LadderChallengeCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LadderPlanOut:
    challenge = db.get(LadderChallenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")

    plan = db.get(LadderPlan, challenge.plan_id)
    if plan is None or plan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Challenge not found")

    existing_checkin = db.scalar(select(Checkin).where(Checkin.challenge_id == challenge.id))
    if existing_checkin is None:
        db.add(
            Checkin(
                challenge_id=challenge.id,
                completed=True,
                photo_url=payload.photo_url,
                lat=payload.lat,
                lng=payload.lng,
            )
        )
    challenge.status = "completed"
    db.commit()

    return latest_ladder_plan(db=db, current_user=current_user)


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
