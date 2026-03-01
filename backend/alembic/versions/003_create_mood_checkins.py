"""Create mood_checkins table.

Revision ID: 003
Revises: 002
Create Date: 2025-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mood_checkins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("veteran_id", sa.Integer(), nullable=False),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("wants_company", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mood_checkins_veteran_id"), "mood_checkins", ["veteran_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mood_checkins_veteran_id"), table_name="mood_checkins")
    op.drop_table("mood_checkins")
