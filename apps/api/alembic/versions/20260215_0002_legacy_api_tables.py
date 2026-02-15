"""legacy api compatibility tables and columns

Revision ID: 20260215_0002
Revises: 20260214_0001
Create Date: 2026-02-15 00:02:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260215_0002"
down_revision = "20260214_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="veteran"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    op.add_column("mood_checkins", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("mood_checkins", sa.Column("wants_company", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    op.add_column("buddy_links", sa.Column("trust_level", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("buddy_links", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_unique_constraint("uq_buddy_link_user_buddy", "buddy_links", ["user_id", "buddy_user_id"])

    op.create_table(
        "buddy_presence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OFFLINE"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_buddy_presence_user_id"),
    )
    op.create_index("ix_buddy_presence_user_id", "buddy_presence", ["user_id"], unique=True)

    op.create_table(
        "sos_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("veteran_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sos_alerts_veteran_id", "sos_alerts", ["veteran_id"], unique=False)

    op.create_table(
        "sos_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sos_alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buddy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NOTIFIED"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("eta_minutes", sa.Integer(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sos_alert_id"], ["sos_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buddy_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sos_recipients_sos_alert_id", "sos_recipients", ["sos_alert_id"], unique=False)
    op.create_index("ix_sos_recipients_buddy_id", "sos_recipients", ["buddy_id"], unique=False)

    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("share_precise_location", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sos_radius_km", sa.Float(), nullable=True, server_default="50.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user_id"),
    )
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"], unique=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")
    op.drop_index("ix_sos_recipients_buddy_id", table_name="sos_recipients")
    op.drop_index("ix_sos_recipients_sos_alert_id", table_name="sos_recipients")
    op.drop_table("sos_recipients")
    op.drop_index("ix_sos_alerts_veteran_id", table_name="sos_alerts")
    op.drop_table("sos_alerts")
    op.drop_index("ix_buddy_presence_user_id", table_name="buddy_presence")
    op.drop_table("buddy_presence")
    op.drop_constraint("uq_buddy_link_user_buddy", "buddy_links", type_="unique")
    op.drop_column("buddy_links", "created_at")
    op.drop_column("buddy_links", "trust_level")
    op.drop_column("mood_checkins", "wants_company")
    op.drop_column("mood_checkins", "tags")
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
