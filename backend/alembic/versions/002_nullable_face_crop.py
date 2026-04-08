"""Make id_face_crop_url nullable (face crop upload removed from registration)

Revision ID: 002_nullable_face_crop
Revises: 001_v2_schema
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa


revision = "002_nullable_face_crop"
down_revision = "001_v2_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "media_applications",
        "id_face_crop_url",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "media_applications",
        "id_face_crop_url",
        existing_type=sa.Text(),
        nullable=False,
    )
