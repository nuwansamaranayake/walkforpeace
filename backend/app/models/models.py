"""SQLAlchemy database models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class MediaType(str, enum.Enum):
    PRINT = "print"
    TV = "tv"
    RADIO = "radio"
    ONLINE = "online"
    PHOTOGRAPHER = "photographer"
    FREELANCE = "freelance"


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class VerificationResult(str, enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    REVOKED = "revoked"


class MediaApplication(Base):
    __tablename__ = "media_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ref_number = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=False)
    designation = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    country = Column(String(100), nullable=False)
    media_type = Column(
        Enum(MediaType, name="media_type_enum", create_constraint=True),
        nullable=False,
    )

    # Image uploads (ID document + live face photo)
    id_document_url = Column(Text, nullable=False)  # Full ID document
    id_face_crop_url = Column(Text, nullable=True)   # Legacy — no longer collected
    face_photo_url = Column(Text, nullable=False)    # Live camera capture

    face_match_score = Column(Float, nullable=True)  # 0.0 to 1.0
    face_match_flagged = Column(
        Boolean, default=False
    )  # True if score < threshold

    # v2: PIN-based retrieval and ID info
    pin_code = Column(String(20), unique=True, nullable=True, index=True)
    id_number = Column(String(50), nullable=True, index=True)
    id_type = Column(String(20), nullable=True, default="nic")
    ocr_extracted_name = Column(String(200), nullable=True)
    ocr_extracted_id = Column(String(50), nullable=True)

    status = Column(
        Enum(
            ApplicationStatus,
            name="application_status_enum",
            create_constraint=True,
        ),
        nullable=False,
        default=ApplicationStatus.PENDING,
        index=True,
    )
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    credential = relationship(
        "Credential", back_populates="application", uselist=False
    )
    reviewer = relationship("AdminUser", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_media_applications_status_created", "status", "created_at"),
    )


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_applications.id"),
        unique=True,
        nullable=False,
    )
    credential_token = Column(String(500), unique=True, nullable=False, index=True)
    qr_code_url = Column(Text, nullable=True)
    badge_pdf_url = Column(Text, nullable=True)
    badge_number = Column(String(20), unique=True, nullable=False)

    issued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    verification_status = Column(
        String(20), nullable=False, default="pending"
    )  # pending | approved | flagged | rejected | revoked

    application = relationship("MediaApplication", back_populates="credential")
    verification_logs = relationship("VerificationLog", back_populates="credential")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    last_login = Column(DateTime(timezone=True), nullable=True)


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id = Column(
        UUID(as_uuid=True),
        ForeignKey("credentials.id"),
        nullable=False,
    )
    scanned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    scanned_by_ip = Column(String(50), nullable=True)
    result = Column(
        Enum(
            VerificationResult,
            name="verification_result_enum",
            create_constraint=True,
        ),
        nullable=False,
    )
    verified_by_action = Column(
        String(20), nullable=True
    )  # null | "gate_approved" | "gate_denied"

    # GPS location tracking (Task 2)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_name = Column(String(200), nullable=True)
    device_id = Column(String(100), nullable=True)  # browser session ID

    # Link to verify session for gatekeeper tracking
    verify_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verify_sessions.id"),
        nullable=True,
    )

    credential = relationship("Credential", back_populates="verification_logs")
