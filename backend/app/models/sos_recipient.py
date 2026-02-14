"""SOS recipient model - buddy notified for an SOS alert."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SosRecipient(Base):
    """Buddy notified for an SOS alert."""

    __tablename__ = "sos_recipients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sos_alert_id: Mapped[int] = mapped_column(ForeignKey("sos_alerts.id", ondelete="CASCADE"), nullable=False)
    buddy_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOTIFIED")  # NOTIFIED | ACCEPTED | DECLINED | NO_RESPONSE
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
