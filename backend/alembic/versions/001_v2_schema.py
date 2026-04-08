"""v2 multi-subdomain schema: PIN codes, OCR fields, verify sessions, verification_status

Revision ID: 001_v2_schema
Revises: None (first migration — v1 tables created by init_db)
Create Date: 2026-04-08
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "001_v2_schema"
down_revision = None
branch_labels = None
depends_on = None


def _generate_pin() -> str:
    """Generate a unique WFP-XXXXXX PIN code."""
    import random
    return f"WFP-{random.randint(100000, 999999):06d}"


def upgrade() -> None:
    # --- 1. New columns on media_applications ---
    op.add_column(
        "media_applications",
        sa.Column("pin_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "media_applications",
        sa.Column("id_number", sa.String(50), nullable=True),
    )
    op.add_column(
        "media_applications",
        sa.Column("id_type", sa.String(20), nullable=True, server_default="nic"),
    )
    op.add_column(
        "media_applications",
        sa.Column("ocr_extracted_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "media_applications",
        sa.Column("ocr_extracted_id", sa.String(50), nullable=True),
    )

    # Backfill unique PINs for existing rows BEFORE adding unique constraint
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id FROM media_applications WHERE pin_code IS NULL")
    ).fetchall()
    for row in rows:
        # Loop until unique (collision unlikely but safe)
        while True:
            pin = _generate_pin()
            exists = conn.execute(
                sa.text("SELECT 1 FROM media_applications WHERE pin_code = :pin"),
                {"pin": pin},
            ).fetchone()
            if not exists:
                conn.execute(
                    sa.text("UPDATE media_applications SET pin_code = :pin WHERE id = :id"),
                    {"pin": pin, "id": row[0]},
                )
                break

    # Now add unique index on pin_code
    op.create_index("ix_media_applications_pin_code", "media_applications", ["pin_code"], unique=True)
    op.create_index("ix_media_applications_id_number", "media_applications", ["id_number"])

    # --- 2. New column on credentials ---
    op.add_column(
        "credentials",
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
    )

    # --- 3. New column on verification_logs ---
    op.add_column(
        "verification_logs",
        sa.Column("verified_by_action", sa.String(20), nullable=True),
    )

    # --- 4. New table: verify_sessions ---
    op.create_table(
        "verify_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("session_token", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_ip", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("verify_sessions")
    op.drop_column("verification_logs", "verified_by_action")
    op.drop_column("credentials", "verification_status")
    op.drop_index("ix_media_applications_id_number", table_name="media_applications")
    op.drop_index("ix_media_applications_pin_code", table_name="media_applications")
    op.drop_column("media_applications", "ocr_extracted_id")
    op.drop_column("media_applications", "ocr_extracted_name")
    op.drop_column("media_applications", "id_type")
    op.drop_column("media_applications", "id_number")
    op.drop_column("media_applications", "pin_code")
