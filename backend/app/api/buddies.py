"""Buddy links API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.buddy_presence import BuddyPresence
from app.models.user import User
from app.schemas.buddy_link import BuddyInviteRequest, BuddyLinkResponse, BuddyLinkWithUser
from app.services.buddy_service import (
    accept_invite,
    block_link,
    get_accepted_links_for_buddy,
    get_buddy_links_for_veteran,
    get_pending_invites_for_buddy,
    invite_buddy,
)

router = APIRouter(prefix="/buddies", tags=["buddies"])


def _enrich_link(link, db: Session, current_user_id: int) -> BuddyLinkWithUser:
    """Add other person's info (including location and presence) to link."""
    other_id = link.buddy_id if link.veteran_id == current_user_id else link.veteran_id
    other = db.get(User, other_id)
    pres = db.execute(select(BuddyPresence).where(BuddyPresence.user_id == other_id)).scalar_one_or_none()
    presence_status = pres.status if pres else "OFFLINE"
    return BuddyLinkWithUser(
        id=link.id,
        veteran_id=link.veteran_id,
        buddy_id=link.buddy_id,
        status=link.status,
        trust_level=link.trust_level,
        created_at=link.created_at,
        other_email=other.email if other else "",
        other_name=other.full_name if other else "",
        other_latitude=other.latitude if other else None,
        other_longitude=other.longitude if other else None,
        other_presence_status=presence_status,
    )


@router.post("/invite", response_model=BuddyLinkResponse)
def invite(
    data: BuddyInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Any user invites another by email or user_id."""
    if not data.buddy_email and not data.buddy_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide buddy_email or buddy_id",
        )
    try:
        link = invite_buddy(
            db,
            veteran_id=current_user.id,
            buddy_email=data.buddy_email,
            buddy_id=data.buddy_id,
            trust_level=data.trust_level,
        )
        return link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{link_id}/accept", response_model=BuddyLinkResponse)
def accept(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buddy accepts an invite."""
    try:
        link = accept_invite(db, link_id, current_user.id)
        return link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{link_id}/block", response_model=BuddyLinkResponse)
def block(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Veteran or buddy blocks the link."""
    try:
        link = block_link(db, link_id, current_user.id)
        return link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[BuddyLinkWithUser])
def list_buddies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get buddy links for current user (as veteran: accepted/pending; as buddy: pending invites + accepted connections)."""
    links = get_buddy_links_for_veteran(db, current_user.id)
    pending_as_buddy = get_pending_invites_for_buddy(db, current_user.id)
    accepted_as_buddy = get_accepted_links_for_buddy(db, current_user.id)

    seen = {l.id for l in links}
    for link in pending_as_buddy:
        if link.id not in seen:
            links.append(link)
            seen.add(link.id)
    for link in accepted_as_buddy:
        if link.id not in seen:
            links.append(link)
            seen.add(link.id)

    return [_enrich_link(link, db, current_user.id) for link in links]
