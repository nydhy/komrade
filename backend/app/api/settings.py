"""User settings + report/block API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.buddy_link import BuddyLink
from app.models.report import Report
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.settings import ReportCreate, UserSettingsResponse, UserSettingsUpdate

router = APIRouter(tags=["settings"])


def _get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    s = db.execute(stmt).scalar_one_or_none()
    if not s:
        s = UserSettings(user_id=user_id, share_precise_location=True, sos_radius_km=50.0)
        db.add(s)
        db.flush()
    return s


@router.get("/settings/me", response_model=UserSettingsResponse)
def get_my_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's settings."""
    s = _get_or_create_settings(db, current_user.id)
    db.commit()
    return s


@router.put("/settings/me", response_model=UserSettingsResponse)
def update_my_settings(
    data: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's settings."""
    s = _get_or_create_settings(db, current_user.id)
    if data.quiet_hours_start is not None:
        s.quiet_hours_start = data.quiet_hours_start
    if data.quiet_hours_end is not None:
        s.quiet_hours_end = data.quiet_hours_end
    if data.share_precise_location is not None:
        s.share_precise_location = data.share_precise_location
    if data.sos_radius_km is not None:
        s.sos_radius_km = data.sos_radius_km
    db.commit()
    db.refresh(s)
    return s


@router.post("/report", status_code=201)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Report a user."""
    if data.reported_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot report yourself")
    target = db.get(User, data.reported_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    report = Report(
        reporter_id=current_user.id,
        reported_user_id=data.reported_user_id,
        reason=data.reason,
    )
    db.add(report)
    db.commit()
    return {"status": "reported", "report_id": report.id}


@router.post("/buddies/{link_id}/block")
def block_buddy(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Block a buddy link."""
    link = db.get(BuddyLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.veteran_id != current_user.id and link.buddy_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your buddy link")
    link.status = "BLOCKED"
    db.commit()
    return {"status": "blocked"}
