"""SOS alert model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SosAlert(Base):
    """SOS alert raised by a veteran."""

    __tablename__ = "sos_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    veteran_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # MOOD | MANUAL
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # LOW | MED | HIGH
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")  # OPEN | ESCALATED | CLOSED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
