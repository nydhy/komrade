"""Buddy link service."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.buddy_link import BuddyLink
from app.models.user import User
from app.services.auth_service import get_user_by_email


def _get_user_by_id(db: Session, user_id: int) -> User | None:
    """Get user by id."""
    return db.get(User, user_id)


def invite_buddy(
    db: Session,
    veteran_id: int,
    buddy_email: str | None = None,
    buddy_id: int | None = None,
    trust_level: int = 3,
) -> BuddyLink:
    """Create a buddy invite. Any user invites another by email or user_id."""
    buddy: User | None = None
    if buddy_email:
        buddy = get_user_by_email(db, buddy_email)
    elif buddy_id:
        buddy = _get_user_by_id(db, buddy_id)

    if not buddy:
        raise ValueError("User not found")

    if buddy.id == veteran_id:
        raise ValueError("Cannot invite yourself")

    # Check both directions for existing links
    existing = db.execute(
        select(BuddyLink).where(
            or_(
                (BuddyLink.veteran_id == veteran_id) & (BuddyLink.buddy_id == buddy.id),
                (BuddyLink.veteran_id == buddy.id) & (BuddyLink.buddy_id == veteran_id),
            )
        )
    ).scalar_one_or_none()

    if existing:
        if existing.status == "BLOCKED":
            raise ValueError("This connection has been blocked")
        if existing.status == "ACCEPTED":
            raise ValueError("Already connected with this user")
        raise ValueError("Invite already pending")

    link = BuddyLink(
        veteran_id=veteran_id,
        buddy_id=buddy.id,
        status="PENDING",
        trust_level=trust_level,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def accept_invite(db: Session, link_id: int, user_id: int) -> BuddyLink:
    """The invited user (buddy_id) accepts the invite."""
    link = db.get(BuddyLink, link_id)
    if not link:
        raise ValueError("Link not found")
    if link.buddy_id != user_id:
        raise ValueError("Only the invited user can accept")
    if link.status != "PENDING":
        raise ValueError(f"Cannot accept link with status {link.status}")

    link.status = "ACCEPTED"
    db.commit()
    db.refresh(link)
    return link


def block_link(db: Session, link_id: int, user_id: int) -> BuddyLink:
    """Block a buddy link. Either veteran or buddy can block."""
    link = db.get(BuddyLink, link_id)
    if not link:
        raise ValueError("Link not found")
    if link.veteran_id != user_id and link.buddy_id != user_id:
        raise ValueError("Only veteran or buddy can block this link")

    link.status = "BLOCKED"
    db.commit()
    db.refresh(link)
    return link


def get_buddy_links_for_veteran(db: Session, veteran_id: int) -> list[BuddyLink]:
    """Get all buddy links for a veteran (accepted and pending)."""
    result = db.execute(
        select(BuddyLink)
        .where(BuddyLink.veteran_id == veteran_id)
        .where(BuddyLink.status.in_(["PENDING", "ACCEPTED"]))
        .order_by(BuddyLink.created_at.desc())
    )
    return list(result.scalars().all())


def get_pending_invites_for_buddy(db: Session, buddy_id: int) -> list[BuddyLink]:
    """Get pending invites where user is the buddy."""
    result = db.execute(
        select(BuddyLink)
        .where(BuddyLink.buddy_id == buddy_id)
        .where(BuddyLink.status == "PENDING")
        .order_by(BuddyLink.created_at.desc())
    )
    return list(result.scalars().all())


def get_accepted_links_for_buddy(db: Session, buddy_id: int) -> list[BuddyLink]:
    """Get accepted links where user is the buddy (so buddy sees their connections)."""
    result = db.execute(
        select(BuddyLink)
        .where(BuddyLink.buddy_id == buddy_id)
        .where(BuddyLink.status == "ACCEPTED")
        .order_by(BuddyLink.created_at.desc())
    )
    return list(result.scalars().all())


def get_all_links_for_user(db: Session, user_id: int) -> list[BuddyLink]:
    """Get all links where user is veteran or buddy (for display)."""
    result = db.execute(
        select(BuddyLink)
        .where(or_(BuddyLink.veteran_id == user_id, BuddyLink.buddy_id == user_id))
        .where(BuddyLink.status.in_(["PENDING", "ACCEPTED"]))
        .order_by(BuddyLink.created_at.desc())
    )
    return list(result.scalars().all())
