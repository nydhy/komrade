"""Journey progress model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class JourneyProgress(Base):
    """Aggregated journey stats and latest selections for a user."""

    __tablename__ = "journey_progress"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_journey_progress_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    active_challenge_id: Mapped[int | None] = mapped_column(
        ForeignKey("challenges.id", ondelete="SET NULL"),
        nullable=True,
    )
    xp_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_feeling: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avoidance_list: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
