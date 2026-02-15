"""Initial schema.

Revision ID: ee7df32c624f
Revises:
Create Date: 2026-02-14 23:47:15.529861

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ee7df32c624f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop legacy/current tables if present so this initial revision can bootstrap
    # a clean schema from older local DB states.
    for table_name in (
        "sos_recipients",
        "sos_alerts",
        "reports",
        "mood_checkins",
        "buddy_presence",
        "buddy_links",
        "user_settings",
        "checkins",
        "ladder_challenges",
        "ladder_plans",
        "alerts",
        "users",
    ):
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("users_pkey")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "buddy_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("veteran_id", sa.Integer(), nullable=False),
        sa.Column("buddy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trust_level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["buddy_id"], ["users.id"], name=op.f("buddy_links_buddy_id_fkey"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], name=op.f("buddy_links_veteran_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("buddy_links_pkey")),
        sa.UniqueConstraint("veteran_id", "buddy_id", name="uq_buddy_link_veteran_buddy"),
    )

    op.create_table(
        "buddy_presence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("buddy_presence_user_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("buddy_presence_pkey")),
        sa.UniqueConstraint("user_id", name=op.f("buddy_presence_user_id_key")),
    )

    op.create_table(
        "mood_checkins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("veteran_id", sa.Integer(), nullable=False),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("wants_company", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], name=op.f("mood_checkins_veteran_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("mood_checkins_pkey")),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("reported_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"], name=op.f("reports_reported_user_id_fkey"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], name=op.f("reports_reporter_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("reports_pkey")),
    )

    op.create_table(
        "sos_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("veteran_id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], name=op.f("sos_alerts_veteran_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("sos_alerts_pkey")),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("share_precise_location", sa.Boolean(), nullable=False),
        sa.Column("sos_radius_km", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("user_settings_user_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("user_settings_pkey")),
        sa.UniqueConstraint("user_id", name=op.f("user_settings_user_id_key")),
    )

    op.create_table(
        "sos_recipients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sos_alert_id", sa.Integer(), nullable=False),
        sa.Column("buddy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("eta_minutes", sa.Integer(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["buddy_id"], ["users.id"], name=op.f("sos_recipients_buddy_id_fkey"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sos_alert_id"], ["sos_alerts.id"], name=op.f("sos_recipients_sos_alert_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("sos_recipients_pkey")),
    )


def downgrade() -> None:
    op.drop_table("sos_recipients")
    op.drop_table("user_settings")
    op.drop_table("sos_alerts")
    op.drop_table("reports")
    op.drop_table("mood_checkins")
    op.drop_table("buddy_presence")
    op.drop_table("buddy_links")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
