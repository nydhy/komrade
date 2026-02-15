"""Add location to users and create buddy_presence table.

Revision ID: 005
Revises: 004
Create Date: 2025-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lat/lng to users
    op.add_column("users", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("longitude", sa.Float(), nullable=True))

    # Create buddy_presence table
    op.create_table(
        "buddy_presence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OFFLINE"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_buddy_presence_user_id"),
    )
    op.create_index(op.f("ix_buddy_presence_user_id"), "buddy_presence", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_buddy_presence_user_id"), table_name="buddy_presence")
    op.drop_table("buddy_presence")
    op.drop_column("users", "longitude")
    op.drop_column("users", "latitude")
