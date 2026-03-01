"""Create sos_alerts and sos_recipients tables.

Revision ID: 004
Revises: 003
Create Date: 2025-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sos_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("veteran_id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sos_alerts_veteran_id"), "sos_alerts", ["veteran_id"], unique=False)

    op.create_table(
        "sos_recipients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sos_alert_id", sa.Integer(), nullable=False),
        sa.Column("buddy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="NOTIFIED"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("eta_minutes", sa.Integer(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sos_alert_id"], ["sos_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buddy_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sos_recipients_sos_alert_id"), "sos_recipients", ["sos_alert_id"], unique=False)
    op.create_index(op.f("ix_sos_recipients_buddy_id"), "sos_recipients", ["buddy_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sos_recipients_buddy_id"), table_name="sos_recipients")
    op.drop_index(op.f("ix_sos_recipients_sos_alert_id"), table_name="sos_recipients")
    op.drop_table("sos_recipients")
    op.drop_index(op.f("ix_sos_alerts_veteran_id"), table_name="sos_alerts")
    op.drop_table("sos_alerts")
