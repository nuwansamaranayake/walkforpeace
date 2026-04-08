"""Public registration API routes."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid as uuid_module

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import ApplicationStatus, Credential, MediaApplication, MediaType
from app.schemas.schemas import RegisterResponse, StatusResponse, RetrieveResponse, OCRResponse
from app.services.storage import upload_file, validate_file, generate_file_key
from app.services.face_match import compute_face_match
from app.services.email import send_registration_confirmation
from app.services.pin import generate_pin_code
from app.services.ocr import extract_id_info
from app.services.auth import create_credential_token
from app.services.qr_service import generate_qr_code
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["registration"])

# In-memory rate limit store (use Redis in production)
_rate_limits: dict[str, list[float]] = {}


def _check_rate_limit(ip: str) -> bool:
    """Check registration rate limit: N per IP per hour."""
    import time

    now = time.time()
    hour_ago = now - 3600
    if ip not in _rate_limits:
        _rate_limits[ip] = []
    _rate_limits[ip] = [t for t in _rate_limits[ip] if t > hour_ago]
    if len(_rate_limits[ip]) >= settings.RATE_LIMIT_REGISTRATIONS:
        return False
    _rate_limits[ip].append(now)
    return True


def _generate_ref_number() -> str:
    """Generate a unique reference number like WFP-0001."""
    short = uuid.uuid4().hex[:6].upper()
    return f"WFP-{short}"


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: Request,
    full_name: str = Form(..., min_length=2, max_length=200),
    organization: str = Form(..., min_length=2, max_length=200),
    designation: str = Form(..., min_length=2, max_length=200),
    email: str = Form(...),
    phone: str = Form(..., min_length=5, max_length=50),
    country: str = Form(..., min_length=2, max_length=100),
    media_type: str = Form(...),
    terms_accepted: bool = Form(...),
    id_number: Optional[str] = Form(None),
    id_type: str = Form("nic"),
    id_document: UploadFile = File(...),
    id_face_crop: UploadFile = File(...),
    face_photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new media credential application."""
    # Rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(429, "Too many registrations. Try again later.")

    # Validate terms
    if not terms_accepted:
        raise HTTPException(400, "Terms must be accepted")

    # Validate media type
    valid_types = {t.value for t in MediaType}
    if media_type.lower() not in valid_types:
        raise HTTPException(400, f"Invalid media type. Must be one of: {valid_types}")

    # Sanitize text inputs
    for field_name, value in [
        ("full_name", full_name),
        ("organization", organization),
        ("designation", designation),
    ]:
        if "<" in value or ">" in value:
            raise HTTPException(400, f"Invalid characters in {field_name}")

    # Validate files
    for file_obj, label in [
        (id_document, "ID document"),
        (id_face_crop, "ID face crop"),
        (face_photo, "Face photo"),
    ]:
        err = validate_file(file_obj.content_type, file_obj.size or 0)
        if err:
            raise HTTPException(400, f"{label}: {err}")

    # Read file bytes
    id_doc_bytes = await id_document.read()
    id_face_bytes = await id_face_crop.read()
    face_bytes = await face_photo.read()

    # Validate sizes after reading
    for label, data in [
        ("ID document", id_doc_bytes),
        ("ID face crop", id_face_bytes),
        ("Face photo", face_bytes),
    ]:
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(400, f"{label} exceeds 5MB limit")
        if len(data) == 0:
            raise HTTPException(400, f"{label} is empty")

    # Upload files
    id_doc_key = generate_file_key("id-documents", id_document.filename or "id.jpg")
    id_face_key = generate_file_key("id-faces", id_face_crop.filename or "face.jpg")
    face_key = generate_file_key("face-photos", face_photo.filename or "live.jpg")

    id_doc_url = await upload_file(
        id_doc_bytes, id_doc_key, id_document.content_type
    )
    id_face_url = await upload_file(
        id_face_bytes, id_face_key, id_face_crop.content_type
    )
    face_url = await upload_file(face_bytes, face_key, face_photo.content_type)

    # Face matching (async, non-blocking for the user)
    face_score, face_flagged = await compute_face_match(id_face_bytes, face_bytes)

    # Generate reference number
    ref_number = _generate_ref_number()

    # Generate unique PIN code
    pin_code = generate_pin_code()
    for _ in range(10):
        existing = await db.execute(
            select(MediaApplication).where(MediaApplication.pin_code == pin_code)
        )
        if existing.scalar_one_or_none() is None:
            break
        pin_code = generate_pin_code()

    # Create application
    application = MediaApplication(
        id=uuid.uuid4(),
        ref_number=ref_number,
        pin_code=pin_code,
        full_name=full_name.strip(),
        organization=organization.strip(),
        designation=designation.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        country=country.strip(),
        media_type=MediaType(media_type.lower()),
        id_document_url=id_doc_url,
        id_face_crop_url=id_face_url,
        face_photo_url=face_url,
        face_match_score=face_score,
        face_match_flagged=face_flagged,
        id_number=id_number,
        id_type=id_type,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.flush()

    # Create credential immediately
    event_date = datetime.strptime(settings.EVENT_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    expires_at = event_date + timedelta(days=settings.CREDENTIAL_EXPIRE_DAYS_AFTER_EVENT)

    cred_id = uuid_module.uuid4()
    badge_number = f"WFP-{cred_id.hex[:6].upper()}"
    credential_token = create_credential_token(str(cred_id), expires_at)

    verification_status = "flagged" if face_flagged else "pending"

    qr_bytes = generate_qr_code(credential_token)
    qr_key = generate_file_key("qr-codes", f"{badge_number}.png")
    qr_url = await upload_file(qr_bytes, qr_key, "image/png")

    credential = Credential(
        id=cred_id,
        application_id=application.id,
        credential_token=credential_token,
        qr_code_url=qr_url,
        badge_number=badge_number,
        expires_at=expires_at,
        verification_status=verification_status,
    )
    db.add(credential)
    await db.flush()

    # Send confirmation email (non-blocking, don't fail registration)
    try:
        send_registration_confirmation(email, full_name, ref_number)
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")

    logger.info(f"New registration: {ref_number} - {full_name} ({organization})")

    return RegisterResponse(
        ref_number=ref_number,
        pin_code=pin_code,
        message="Application submitted successfully. Save your PIN to retrieve your QR code.",
        status="pending_review",
        qr_code_url=qr_url,
    )


@router.get("/register/status/{ref_number}", response_model=StatusResponse)
async def check_status(ref_number: str, db: AsyncSession = Depends(get_db)):
    """Check application status by reference number."""
    result = await db.execute(
        select(MediaApplication).where(MediaApplication.ref_number == ref_number)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")

    return StatusResponse(
        ref_number=app.ref_number,
        full_name=app.full_name,
        organization=app.organization,
        status=app.status.value,
        submitted_at=app.created_at,
        reviewed_at=app.reviewed_at,
    )


@router.get("/register/retrieve", response_model=RetrieveResponse)
async def retrieve_credential(
    pin: Optional[str] = Query(None),
    id_number: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve credential by PIN code or NIC/passport number."""
    if not pin and not id_number:
        raise HTTPException(400, "Provide either 'pin' or 'id_number' query parameter")

    query = select(MediaApplication).options(
        selectinload(MediaApplication.credential)
    )
    if pin:
        query = query.where(MediaApplication.pin_code == pin)
    else:
        query = query.where(MediaApplication.id_number == id_number)

    result = await db.execute(query)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "No application found for the given credentials")

    cred = app.credential
    vs = cred.verification_status if cred else "pending"

    messages = {
        "approved": "Your credential is approved. Show the QR code at the event.",
        "pending": "Your application is under review. You will be notified once approved.",
        "flagged": "Your application is under review. Please bring your original ID to the event.",
        "rejected": "Your application has been rejected.",
        "revoked": "Your credential has been revoked.",
    }

    return RetrieveResponse(
        ref_number=app.ref_number,
        pin_code=app.pin_code,
        full_name=app.full_name,
        organization=app.organization,
        status=app.status.value,
        verification_status=vs,
        qr_code_url=cred.qr_code_url if cred else None,
        badge_pdf_url=cred.badge_pdf_url if cred else None,
        badge_number=cred.badge_number if cred else None,
        message=messages.get(vs, "Unknown status"),
    )


@router.post("/register/ocr", response_model=OCRResponse)
async def ocr_extract(
    id_document: UploadFile = File(...),
):
    """Extract NIC number from ID document image using OCR."""
    err = validate_file(id_document.content_type, id_document.size or 0)
    if err:
        raise HTTPException(400, f"Invalid file: {err}")

    image_bytes = await id_document.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(400, "File exceeds 5MB limit")
    if len(image_bytes) == 0:
        raise HTTPException(400, "File is empty")

    result = extract_id_info(image_bytes)

    return OCRResponse(
        id_number=result.get("id_number"),
        name=result.get("name"),
        confidence=result.get("confidence"),
    )
