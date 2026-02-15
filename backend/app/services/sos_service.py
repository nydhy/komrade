"""SOS alert service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.sos_policies import COOLDOWN_SECONDS, DEFAULT_SOS_RADIUS_KM, ESCALATE_AFTER_MIN, ESCALATE_MORE_RECIPIENTS, MIN_BUDDIES_FOR_SOS
from app.models.mood_checkin import MoodCheckin
from app.models.sos_alert import SosAlert
from app.models.sos_recipient import SosRecipient
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.buddy_service import get_all_accepted_buddy_ids
from app.services.geo_service import get_ranked_buddies


def _get_sos_radius(db: Session, user_id: int) -> float:
    """Get user's SOS radius from settings, falling back to default."""
    from sqlalchemy import select as sel
    stmt = sel(UserSettings).where(UserSettings.user_id == user_id)
    settings = db.execute(stmt).scalar_one_or_none()
    if settings and settings.sos_radius_km is not None:
        return settings.sos_radius_km
    return DEFAULT_SOS_RADIUS_KM


def _select_best_buddies(db: Session, veteran_id: int, n: int) -> list[int]:
    """Select best N buddies using ranking (availability + trust + distance), filtered by SOS radius.
    
    SOS is an emergency feature: if no online buddies are found within radius,
    falls back to ALL accepted buddies (ignoring presence/radius) to ensure
    the alert still reaches someone.
    """
    radius = _get_sos_radius(db, veteran_id)
    ranked = get_ranked_buddies(db, veteran_id, limit=n, radius_km=radius)
    selected = [r.buddy_id for r in ranked]
    
    # Fallback: if nobody is online within radius, use all accepted buddies
    if not selected:
        all_ids = get_all_accepted_buddy_ids(db, veteran_id)
        selected = all_ids[:n]
    
    return selected


def _check_cooldown(db: Session, veteran_id: int) -> None:
    """Raise if veteran created an SOS within cooldown window."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=COOLDOWN_SECONDS)
    stmt = (
        select(SosAlert)
        .where(
            SosAlert.veteran_id == veteran_id,
            SosAlert.created_at >= cutoff,
        )
        .limit(1)
    )
    recent = db.execute(stmt).scalar_one_or_none()
    if recent:
        raise ValueError(
            f"SOS cooldown active. Please wait {COOLDOWN_SECONDS} seconds between SOS alerts."
        )


def create_sos_manual(
    db: Session,
    veteran_id: int,
    severity: str,
    buddy_ids: list[int] | None = None,
    broadcast: bool = False,
) -> SosAlert:
    """Create manual SOS.
    - If buddy_ids provided: send only to those (must be accepted).
    - If broadcast=True: send to all accepted buddies.
    - Otherwise: auto-select 3-5 best-ranked.
    """
    _check_cooldown(db, veteran_id)
    all_ids = get_all_accepted_buddy_ids(db, veteran_id)
    if len(all_ids) < MIN_BUDDIES_FOR_SOS:
        raise ValueError(f"Need at least {MIN_BUDDIES_FOR_SOS} accepted buddy/buddies to create SOS")

    if buddy_ids is not None and len(buddy_ids) > 0:
        invalid = [bid for bid in buddy_ids if bid not in all_ids]
        if invalid:
            # #region agent log
            try:
                import json
                with open("/Users/sriramm/Cursor_Projects/.cursor/debug.log", "a") as f:
                    f.write(json.dumps({"location":"sos_service.py:create_sos_manual","message":"Invalid buddy IDs","data":{"veteran_id":veteran_id,"buddy_ids":buddy_ids,"all_ids":all_ids,"invalid":invalid},"timestamp":__import__("time").time()*1000,"hypothesisId":"H2"}) + "\n")
            except Exception:
                pass
            # #endregion
            raise ValueError(f"Invalid buddy IDs (not accepted): {invalid}")
        selected = buddy_ids
    elif broadcast:
        selected = all_ids
    else:
        n = min(5, len(all_ids))
        selected = _select_best_buddies(db, veteran_id, n)

    alert = SosAlert(
        veteran_id=veteran_id,
        trigger_type="MANUAL",
        severity=severity,
        status="OPEN",
    )
    db.add(alert)
    db.flush()

    for bid in selected:
        rec = SosRecipient(sos_alert_id=alert.id, buddy_id=bid, status="NOTIFIED")
        db.add(rec)

    db.commit()
    db.refresh(alert)
    # #region agent log
    try:
        import json
        with open("/Users/sriramm/Cursor_Projects/.cursor/debug.log", "a") as f:
            f.write(json.dumps({"location":"sos_service.py:create_sos_manual","message":"SOS created","data":{"alert_id":alert.id,"veteran_id":veteran_id,"selected":selected},"timestamp":__import__("time").time()*1000,"hypothesisId":"H2"}) + "\n")
    except Exception:
        pass
    # #endregion
    return alert


def create_sos_from_checkin(
    db: Session,
    veteran_id: int,
    checkin_id: int,
    severity: str = "MED",
    buddy_ids: list[int] | None = None,
    broadcast: bool = False,
) -> SosAlert:
    """Create SOS from mood check-in if wants_company or mood low (1-2).
    - If buddy_ids provided: send only to those (must be accepted).
    - If broadcast=True: send to all accepted buddies.
    - Otherwise: auto-select 3-5 best-ranked.
    """
    checkin = db.get(MoodCheckin, checkin_id)
    if not checkin:
        raise ValueError("Check-in not found")
    if checkin.veteran_id != veteran_id:
        raise ValueError("Check-in does not belong to you")
    if not checkin.wants_company and checkin.mood_score > 2:
        raise ValueError("Check-in does not trigger SOS (need wants_company or mood 1-2)")

    _check_cooldown(db, veteran_id)
    all_ids = get_all_accepted_buddy_ids(db, veteran_id)
    if len(all_ids) < MIN_BUDDIES_FOR_SOS:
        raise ValueError(f"Need at least {MIN_BUDDIES_FOR_SOS} accepted buddy/buddies to create SOS")

    if buddy_ids is not None and len(buddy_ids) > 0:
        invalid = [bid for bid in buddy_ids if bid not in all_ids]
        if invalid:
            raise ValueError(f"Invalid buddy IDs (not accepted): {invalid}")
        selected = buddy_ids
    elif broadcast:
        selected = all_ids
    else:
        n = min(5, len(all_ids))
        selected = _select_best_buddies(db, veteran_id, n)

    alert = SosAlert(
        veteran_id=veteran_id,
        trigger_type="MOOD",
        severity=severity,
        status="OPEN",
    )
    db.add(alert)
    db.flush()

    for bid in selected:
        rec = SosRecipient(sos_alert_id=alert.id, buddy_id=bid, status="NOTIFIED")
        db.add(rec)

    db.commit()
    db.refresh(alert)
    return alert


def list_my_sos(db: Session, user_id: int, limit: int = 20) -> list[SosAlert]:
    """List SOS alerts for veteran, newest first."""
    result = db.execute(
        select(SosAlert)
        .where(SosAlert.veteran_id == user_id)
        .order_by(SosAlert.created_at.desc(), SosAlert.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def get_sos(db: Session, sos_id: int, user_id: int) -> SosAlert | None:
    """Get SOS by id. Only veteran owner can view."""
    alert = db.get(SosAlert, sos_id)
    if not alert or alert.veteran_id != user_id:
        return None
    return alert


def delete_sos(db: Session, sos_id: int, user_id: int) -> None:
    """Delete an SOS alert and its recipients. Only veteran owner can delete."""
    alert = db.get(SosAlert, sos_id)
    if not alert:
        raise ValueError("SOS not found")
    if alert.veteran_id != user_id:
        raise ValueError("Only the veteran who created this SOS can delete it")

    # Delete recipients first (foreign key), then the alert
    db.execute(
        select(SosRecipient).where(SosRecipient.sos_alert_id == sos_id)
    )
    for rec in db.execute(select(SosRecipient).where(SosRecipient.sos_alert_id == sos_id)).scalars().all():
        db.delete(rec)
    db.delete(alert)
    db.commit()


def close_sos(db: Session, sos_id: int, user_id: int) -> SosAlert:
    """Close SOS. Only veteran owner can close."""
    alert = db.get(SosAlert, sos_id)
    if not alert:
        raise ValueError("SOS not found")
    if alert.veteran_id != user_id:
        raise ValueError("Only the veteran who created this SOS can close it")
    if alert.status == "CLOSED":
        raise ValueError("SOS is already closed")

    alert.status = "CLOSED"
    alert.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


# ---------- Module 8: Escalation ----------


def escalate_sos(db: Session, sos_id: int, user_id: int) -> SosAlert:
    """Add more recipients if no one accepted. Only owner veteran. Idempotent."""
    alert = db.get(SosAlert, sos_id)
    if not alert:
        raise ValueError("SOS not found")
    if alert.veteran_id != user_id:
        raise ValueError("Only the veteran who created this SOS can escalate it")
    if alert.status == "CLOSED":
        raise ValueError("Cannot escalate a closed SOS")

    # Check if elapsed time allows escalation
    elapsed = datetime.now(timezone.utc) - alert.created_at.replace(tzinfo=timezone.utc)
    if elapsed < timedelta(minutes=ESCALATE_AFTER_MIN):
        raise ValueError(
            f"Cannot escalate yet. Wait at least {ESCALATE_AFTER_MIN} minutes after SOS creation."
        )

    # Check no one accepted
    stmt = select(SosRecipient).where(
        SosRecipient.sos_alert_id == sos_id,
        SosRecipient.status == "ACCEPTED",
    )
    if db.execute(stmt).first():
        raise ValueError("Cannot escalate — a buddy has already accepted.")

    # Get existing recipient buddy IDs
    existing_stmt = select(SosRecipient.buddy_id).where(SosRecipient.sos_alert_id == sos_id)
    existing_ids = set(db.execute(existing_stmt).scalars().all())

    # Get all accepted buddies, filter out existing
    all_ids = get_all_accepted_buddy_ids(db, alert.veteran_id)
    candidates = [bid for bid in all_ids if bid not in existing_ids]
    if not candidates:
        raise ValueError("No additional buddies available to escalate to.")

    # Pick up to ESCALATE_MORE_RECIPIENTS new buddies using ranking
    ranked = get_ranked_buddies(db, alert.veteran_id, limit=len(all_ids))
    new_buddies = [r.buddy_id for r in ranked if r.buddy_id not in existing_ids][:ESCALATE_MORE_RECIPIENTS]

    if not new_buddies:
        raise ValueError("No additional buddies available to escalate to.")

    for bid in new_buddies:
        rec = SosRecipient(sos_alert_id=alert.id, buddy_id=bid, status="NOTIFIED")
        db.add(rec)

    alert.status = "ESCALATED"
    db.commit()
    db.refresh(alert)
    return alert


# ---------- Module 6: Buddy Inbox + Respond ----------


def get_incoming_alerts(db: Session, buddy_id: int) -> list[dict]:
    """Get SOS alerts where this buddy is a recipient (pending / all)."""
    stmt = (
        select(SosRecipient, SosAlert, User)
        .join(SosAlert, SosRecipient.sos_alert_id == SosAlert.id)
        .join(User, SosAlert.veteran_id == User.id)
        .where(SosRecipient.buddy_id == buddy_id)
        .order_by(SosAlert.created_at.desc(), SosAlert.id.desc())
    )
    rows = db.execute(stmt).all()
    result = []
    for rec, alert, veteran in rows:
        result.append(
            {
                "alert_id": alert.id,
                "veteran_id": alert.veteran_id,
                "veteran_name": veteran.full_name,
                "trigger_type": alert.trigger_type,
                "severity": alert.severity,
                "alert_status": alert.status,
                "created_at": alert.created_at,
                "recipient_id": rec.id,
                "my_status": rec.status,
                "my_message": rec.message,
                "my_eta_minutes": rec.eta_minutes,
                "responded_at": rec.responded_at,
            }
        )
    return result


def respond_to_sos(
    db: Session,
    sos_id: int,
    buddy_id: int,
    response_status: str,
    message: str | None = None,
    eta_minutes: int | None = None,
) -> SosRecipient:
    """Buddy responds to SOS. Only recipient buddy can respond. Idempotent."""
    # Find the recipient row for this buddy + alert
    stmt = select(SosRecipient).where(
        SosRecipient.sos_alert_id == sos_id,
        SosRecipient.buddy_id == buddy_id,
    )
    rec = db.execute(stmt).scalar_one_or_none()
    if not rec:
        raise ValueError("You are not a recipient of this SOS alert")

    # Check alert is still OPEN
    alert = db.get(SosAlert, sos_id)
    if not alert or alert.status == "CLOSED":
        raise ValueError("This SOS alert is already closed")

    # Idempotent: if already responded, update the response
    rec.status = response_status
    rec.message = message
    rec.eta_minutes = eta_minutes
    rec.responded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rec)
    return rec
