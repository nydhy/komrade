"""Add journey progress and challenges tables.

Revision ID: 7c59a240f621
Revises: ee7df32c624f
Create Date: 2026-02-15 05:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7c59a240f621"
down_revision: Union[str, None] = "ee7df32c624f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default=sa.text("25")),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("challenges_user_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("challenges_pkey")),
    )
    op.create_index(op.f("ix_challenges_user_id"), "challenges", ["user_id"], unique=False)

    op.create_table(
        "journey_progress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("active_challenge_id", sa.Integer(), nullable=True),
        sa.Column("xp_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("current_feeling", sa.String(length=50), nullable=True),
        sa.Column("next_step", sa.String(length=100), nullable=True),
        sa.Column("avoidance_list", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["active_challenge_id"],
            ["challenges.id"],
            name=op.f("journey_progress_active_challenge_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("journey_progress_user_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("journey_progress_pkey")),
        sa.UniqueConstraint("user_id", name="uq_journey_progress_user"),
    )


def downgrade() -> None:
    op.drop_table("journey_progress")
    op.drop_index(op.f("ix_challenges_user_id"), table_name="challenges")
    op.drop_table("challenges")
