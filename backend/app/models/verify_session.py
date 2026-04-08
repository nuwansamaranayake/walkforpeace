"""Verify subdomain session model — anonymous password-based sessions."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.models.models import Base


class VerifySession(Base):
    __tablename__ = "verify_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(200), unique=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    device_ip = Column(String(50), nullable=True)
    is_expired = Column(Boolean, default=False, nullable=False)  # manual logout flag

    # Gatekeeper device info (Task 4)
    device_info = Column(String(500), nullable=True)   # User-Agent string
    device_name = Column(String(100), nullable=True)   # Parsed: "Samsung Galaxy A12"
    screen_size = Column(String(20), nullable=True)    # "360x800"
    total_scans = Column(Integer, default=0, nullable=False)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_location = Column(String(200), nullable=True)
