"""Verify subdomain session model — anonymous password-based sessions."""
import uuid

from sqlalchemy import Column, DateTime, String, text
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
