"""initial schema

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14 00:01:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


buddy_link_status = postgresql.ENUM("pending", "accepted", name="buddy_link_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "mood_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_mood_checkins_user_id", "mood_checkins", ["user_id"], unique=False)

    buddy_link_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "buddy_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buddy_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            buddy_link_status,
            nullable=False,
            server_default="pending",
        ),
        sa.ForeignKeyConstraint(["buddy_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_buddy_links_user_id", "buddy_links", ["user_id"], unique=False)
    op.create_index("ix_buddy_links_buddy_user_id", "buddy_links", ["buddy_user_id"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_alerts_from_user_id", "alerts", ["from_user_id"], unique=False)
    op.create_index("ix_alerts_to_user_id", "alerts", ["to_user_id"], unique=False)

    op.create_table(
        "ladder_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ladder_plans_user_id", "ladder_plans", ["user_id"], unique=False)

    op.create_table(
        "ladder_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("difficulty", sa.String(length=64), nullable=False),
        sa.Column("suggested_time", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["ladder_plans.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ladder_challenges_plan_id", "ladder_challenges", ["plan_id"], unique=False)

    op.create_table(
        "checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["ladder_challenges.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_checkins_challenge_id", "checkins", ["challenge_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_checkins_challenge_id", table_name="checkins")
    op.drop_table("checkins")

    op.drop_index("ix_ladder_challenges_plan_id", table_name="ladder_challenges")
    op.drop_table("ladder_challenges")

    op.drop_index("ix_ladder_plans_user_id", table_name="ladder_plans")
    op.drop_table("ladder_plans")

    op.drop_index("ix_alerts_to_user_id", table_name="alerts")
    op.drop_index("ix_alerts_from_user_id", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_buddy_links_buddy_user_id", table_name="buddy_links")
    op.drop_index("ix_buddy_links_user_id", table_name="buddy_links")
    op.drop_table("buddy_links")
    buddy_link_status.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_mood_checkins_user_id", table_name="mood_checkins")
    op.drop_table("mood_checkins")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
