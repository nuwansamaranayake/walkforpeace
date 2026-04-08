"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# --- Registration ---
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    organization: str = Field(..., min_length=2, max_length=200)
    designation: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)
    country: str = Field(..., min_length=2, max_length=100)
    media_type: str = Field(...)
    terms_accepted: bool = Field(...)

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, v):
        valid = {"print", "tv", "radio", "online", "photographer", "freelance"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid media type. Must be one of: {valid}")
        return v.lower()

    @field_validator("terms_accepted")
    @classmethod
    def validate_terms(cls, v):
        if not v:
            raise ValueError("Terms must be accepted")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?[0-9]{7,15}$", cleaned):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("full_name", "organization", "designation", "country")
    @classmethod
    def sanitize_text(cls, v):
        # Basic XSS prevention
        v = v.replace("<", "&lt;").replace(">", "&gt;")
        return v.strip()


class RegisterResponse(BaseModel):
    ref_number: str
    pin_code: str
    message: str
    status: str
    qr_code_url: Optional[str] = None


class StatusResponse(BaseModel):
    ref_number: str
    full_name: str
    organization: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None


# --- Admin Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# --- Admin Applications ---
class ApplicationListItem(BaseModel):
    id: UUID
    ref_number: str
    full_name: str
    organization: str
    designation: str
    email: str
    media_type: str
    status: str
    face_match_score: Optional[float] = None
    face_match_flagged: bool = False
    pin_code: Optional[str] = None
    id_number: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationDetail(ApplicationListItem):
    phone: str
    country: str
    id_document_url: str
    id_face_crop_url: Optional[str] = None
    face_photo_url: str
    id_number: Optional[str] = None
    id_type: Optional[str] = None
    ocr_extracted_name: Optional[str] = None
    ocr_extracted_id: Optional[str] = None
    admin_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    updated_at: datetime
    credential: Optional["CredentialInfo"] = None

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    admin_notes: Optional[str] = Field(None, max_length=1000)


class ApplicationListResponse(BaseModel):
    items: list[ApplicationListItem]
    total: int
    page: int
    page_size: int


# --- Credentials ---
class CredentialInfo(BaseModel):
    id: UUID
    credential_token: str
    qr_code_url: Optional[str] = None
    badge_pdf_url: Optional[str] = None
    badge_number: str
    issued_at: datetime
    expires_at: datetime
    is_revoked: bool
    verification_status: str = "pending"

    model_config = {"from_attributes": True}


# --- Verification ---
class VerifyResponse(BaseModel):
    valid: bool
    status: str  # valid, invalid, expired, revoked
    full_name: Optional[str] = None
    organization: Optional[str] = None
    designation: Optional[str] = None
    media_type: Optional[str] = None
    face_photo_url: Optional[str] = None
    badge_number: Optional[str] = None
    message: str


# --- Stats ---
class DashboardStats(BaseModel):
    total_registered: int
    pending: int
    approved: int
    rejected: int
    flagged: int
    credentials_issued: int
    total_scans_today: int = 0
    active_gatekeepers: int = 0


# --- v2: Retrieve ---
class RetrieveResponse(BaseModel):
    ref_number: str
    pin_code: str
    full_name: str
    organization: str
    status: str
    verification_status: str
    qr_code_url: Optional[str] = None
    badge_pdf_url: Optional[str] = None
    badge_number: Optional[str] = None
    message: str


# --- v2: Verify Auth ---
class VerifyAuthRequest(BaseModel):
    password: str


class VerifyAuthResponse(BaseModel):
    session_token: str
    expires_at: datetime


# --- v2: Tiered Verify ---
class VerifyResponseV2(BaseModel):
    valid: bool
    status: str
    verification_status: Optional[str] = None
    full_name: Optional[str] = None
    organization: Optional[str] = None
    designation: Optional[str] = None
    media_type: Optional[str] = None
    face_photo_url: Optional[str] = None
    id_face_crop_url: Optional[str] = None
    face_match_score: Optional[float] = None
    badge_number: Optional[str] = None
    can_gate_approve: Optional[bool] = None
    message: str


# --- v2: Batch Approve ---
class BatchApproveRequest(BaseModel):
    application_ids: list[str]


class BatchApproveResponse(BaseModel):
    approved_count: int
    message: str


# --- v2: Verification Log Entry ---
class VerificationLogItem(BaseModel):
    id: UUID
    credential_id: UUID
    badge_number: Optional[str] = None
    full_name: Optional[str] = None
    scanned_at: datetime
    scanned_by_ip: Optional[str] = None
    result: str
    verified_by_action: Optional[str] = None

    model_config = {"from_attributes": True}


class VerificationLogResponse(BaseModel):
    items: list[VerificationLogItem]
    total: int
    page: int
    page_size: int


# --- Scan Log for per-application scan history (Task 2) ---
class ScanLogItem(BaseModel):
    id: UUID
    scanned_at: datetime
    scanned_by_ip: Optional[str] = None
    result: str
    verified_by_action: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_name: Optional[str] = None
    device_id: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Verify Auth with device info (Task 4) ---
class VerifyAuthRequestV2(BaseModel):
    password: str
    device_info: Optional[str] = None
    device_name: Optional[str] = None
    screen_size: Optional[str] = None


# --- Gatekeeper info (Task 4) ---
class GatekeeperInfo(BaseModel):
    id: UUID
    device_name: Optional[str] = None
    device_ip: Optional[str] = None
    screen_size: Optional[str] = None
    total_scans: int = 0
    last_scan_at: Optional[datetime] = None
    last_location: Optional[str] = None
    created_at: datetime
    status: str = "active"  # active | inactive

    model_config = {"from_attributes": True}


# --- Upload ---
class PresignResponse(BaseModel):
    upload_url: str
    file_url: str
    file_key: str
