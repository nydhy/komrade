"""SOS alerts API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_veteran
from app.core.ws_manager import ws_manager
from app.db.session import get_db
from app.models.sos_recipient import SosRecipient
from app.models.user import User
from app.schemas.sos import (
    IncomingSosAlertResponse,
    SosAlertResponse,
    SosFromCheckinCreate,
    SosManualCreate,
    SosRecipientResponse,
    SosRecipientWithBuddy,
    SosRespondRequest,
)
from app.services.sos_service import (
    close_sos,
    create_sos_from_checkin,
    create_sos_manual,
    escalate_sos,
    get_incoming_alerts,
    get_sos,
    list_my_sos,
    respond_to_sos,
)

router = APIRouter(prefix="/sos", tags=["sos"])


def _enrich_alert(alert, db: Session) -> SosAlertResponse:
    """Add recipients with buddy info."""
    result = db.execute(select(SosRecipient).where(SosRecipient.sos_alert_id == alert.id))
    recipients = list(result.scalars().all())
    enriched = []
    for rec in recipients:
        buddy = db.get(User, rec.buddy_id)
        enriched.append(
            SosRecipientWithBuddy(
                id=rec.id,
                sos_alert_id=rec.sos_alert_id,
                buddy_id=rec.buddy_id,
                status=rec.status,
                message=rec.message,
                eta_minutes=rec.eta_minutes,
                responded_at=rec.responded_at,
                buddy_email=buddy.email if buddy else "",
                buddy_name=buddy.full_name if buddy else "",
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
        recipients=enriched,
    )


@router.get("/me", response_model=list[SosAlertResponse])
def list_my_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_veteran),
):
    """List current user's SOS alerts, newest first."""
    alerts = list_my_sos(db, current_user.id, limit)
    return [_enrich_alert(a, db) for a in alerts]


@router.post("", response_model=SosAlertResponse)
def create_manual(
    data: SosManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_veteran),
):
    """Create manual SOS. Only veterans. Creates 3-5 recipients from accepted buddies."""
    try:
        alert = create_sos_manual(db, current_user.id, data.severity, data.buddy_ids, data.broadcast)
        enriched = _enrich_alert(alert, db)
        _broadcast_sos_created(enriched)
        return enriched
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/from-checkin/{checkin_id}", response_model=SosAlertResponse)
def create_from_checkin(
    checkin_id: int,
    data: SosFromCheckinCreate | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_veteran),
):
    """Create SOS from check-in if wants_company or mood low (1-2)."""
    d = data or SosFromCheckinCreate()
    try:
        alert = create_sos_from_checkin(db, current_user.id, checkin_id, d.severity, d.buddy_ids, d.broadcast)
        enriched = _enrich_alert(alert, db)
        _broadcast_sos_created(enriched)
        return enriched
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---- Module 6: Buddy Inbox + Respond (before {sos_id} path param) ----


@router.get("/incoming", response_model=list[IncomingSosAlertResponse])
def list_incoming(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get SOS alerts where the current user is a recipient (buddy inbox)."""
    return get_incoming_alerts(db, current_user.id)


@router.get("/{sos_id}", response_model=SosAlertResponse)
def get_alert(
    sos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get SOS status/timeline. Only veteran owner can view."""
    alert = get_sos(db, sos_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOS not found")
    return _enrich_alert(alert, db)


@router.post("/{sos_id}/close", response_model=SosAlertResponse)
def close_alert(
    sos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Close SOS. Only veteran owner can close."""
    try:
        alert = close_sos(db, sos_id, current_user.id)
        enriched = _enrich_alert(alert, db)
        _broadcast_sos_closed(enriched)
        return enriched
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{sos_id}/escalate", response_model=SosAlertResponse)
def escalate_alert(
    sos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_veteran),
):
    """Escalate SOS — add more recipients if no buddy accepted yet."""
    try:
        alert = escalate_sos(db, sos_id, current_user.id)
        enriched = _enrich_alert(alert, db)
        _broadcast_sos_created(enriched)  # notify new recipients
        return enriched
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if "only the veteran" in detail.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post("/{sos_id}/respond", response_model=SosRecipientResponse)
def respond_to_alert(
    sos_id: int,
    data: SosRespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buddy responds to SOS (ACCEPTED/DECLINED) with optional message + ETA."""
    try:
        rec = respond_to_sos(
            db,
            sos_id,
            current_user.id,
            data.status,
            data.message,
            data.eta_minutes,
        )
        _broadcast_recipient_updated(db, sos_id, rec)
        return rec
    except ValueError as e:
        detail = str(e)
        if "not a recipient" in detail.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# ---------- WebSocket broadcast helpers ----------


def _broadcast_sos_created(alert_resp: SosAlertResponse) -> None:
    """Notify all recipient buddies about a new SOS."""
    data = alert_resp.model_dump(mode="json")
    buddy_ids = [r.buddy_id for r in alert_resp.recipients]
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(ws_manager.send_to_users(buddy_ids, "sos.created", data))
    except RuntimeError:
        pass  # no event loop (e.g. in tests)


def _broadcast_recipient_updated(db: Session, sos_id: int, rec: SosRecipient) -> None:
    """Notify the veteran that a buddy responded."""
    from app.models.sos_alert import SosAlert

    alert = db.get(SosAlert, sos_id)
    if not alert:
        return
    buddy = db.get(User, rec.buddy_id)
    data = {
        "sos_id": sos_id,
        "recipient_id": rec.id,
        "buddy_id": rec.buddy_id,
        "buddy_name": buddy.full_name if buddy else "",
        "status": rec.status,
        "message": rec.message,
        "eta_minutes": rec.eta_minutes,
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(ws_manager.send_to_user(alert.veteran_id, "sos.recipient_updated", data))
    except RuntimeError:
        pass


def _broadcast_sos_closed(alert_resp: SosAlertResponse) -> None:
    """Notify all recipient buddies that the SOS was closed."""
    data = {"sos_id": alert_resp.id, "status": "CLOSED"}
    buddy_ids = [r.buddy_id for r in alert_resp.recipients]
    all_ids = buddy_ids + [alert_resp.veteran_id]
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(ws_manager.send_to_users(all_ids, "sos.closed", data))
    except RuntimeError:
        pass
