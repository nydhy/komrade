"""add sos_radius_km to user_settings

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"


def upgrade():
    op.add_column("user_settings", sa.Column("sos_radius_km", sa.Float(), nullable=True, server_default="50.0"))


def downgrade():
    op.drop_column("user_settings", "sos_radius_km")
