"""Buddy link model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BuddyLink(Base):
    """Link between a veteran and their trusted buddy."""

    __tablename__ = "buddy_links"
    __table_args__ = (
        UniqueConstraint("veteran_id", "buddy_id", name="uq_buddy_link_veteran_buddy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    veteran_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    buddy_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    trust_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
