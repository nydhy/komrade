"""Create buddy_links table.

Revision ID: 002
Revises: 001
Create Date: 2025-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "buddy_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("veteran_id", sa.Integer(), nullable=False),
        sa.Column("buddy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("trust_level", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["veteran_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buddy_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("veteran_id", "buddy_id", name="uq_buddy_link_veteran_buddy"),
    )
    op.create_index(op.f("ix_buddy_links_veteran_id"), "buddy_links", ["veteran_id"], unique=False)
    op.create_index(op.f("ix_buddy_links_buddy_id"), "buddy_links", ["buddy_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_buddy_links_buddy_id"), table_name="buddy_links")
    op.drop_index(op.f("ix_buddy_links_veteran_id"), table_name="buddy_links")
    op.drop_table("buddy_links")
