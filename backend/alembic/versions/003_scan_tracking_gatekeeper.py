"""Add GPS columns to verification_logs, device/scan tracking to verify_sessions

Revision ID: 003_scan_tracking_gatekeeper
Revises: 002_nullable_face_crop
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "003_scan_tracking_gatekeeper"
down_revision = "002_nullable_face_crop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Task 2: Add GPS + device columns to verification_logs
    op.add_column("verification_logs", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("verification_logs", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("verification_logs", sa.Column("place_name", sa.String(200), nullable=True))
    op.add_column("verification_logs", sa.Column("device_id", sa.String(100), nullable=True))
    op.add_column("verification_logs", sa.Column(
        "verify_session_id", UUID(as_uuid=True), nullable=True,
    ))

    # Task 3: Add is_expired flag to verify_sessions
    op.add_column("verify_sessions", sa.Column(
        "is_expired", sa.Boolean(), nullable=False, server_default=sa.text("false"),
    ))

    # Task 4: Add device info + scan tracking to verify_sessions
    op.add_column("verify_sessions", sa.Column("device_info", sa.String(500), nullable=True))
    op.add_column("verify_sessions", sa.Column("device_name", sa.String(100), nullable=True))
    op.add_column("verify_sessions", sa.Column("screen_size", sa.String(20), nullable=True))
    op.add_column("verify_sessions", sa.Column(
        "total_scans", sa.Integer(), nullable=False, server_default=sa.text("0"),
    ))
    op.add_column("verify_sessions", sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("verify_sessions", sa.Column("last_location", sa.String(200), nullable=True))


def downgrade() -> None:
    # verification_logs
    op.drop_column("verification_logs", "verify_session_id")
    op.drop_column("verification_logs", "device_id")
    op.drop_column("verification_logs", "place_name")
    op.drop_column("verification_logs", "longitude")
    op.drop_column("verification_logs", "latitude")

    # verify_sessions
    op.drop_column("verify_sessions", "last_location")
    op.drop_column("verify_sessions", "last_scan_at")
    op.drop_column("verify_sessions", "total_scans")
    op.drop_column("verify_sessions", "screen_size")
    op.drop_column("verify_sessions", "device_name")
    op.drop_column("verify_sessions", "device_info")
    op.drop_column("verify_sessions", "is_expired")
