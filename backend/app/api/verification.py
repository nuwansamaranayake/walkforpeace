"""Public verification API route for QR code scanning."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import Credential, MediaApplication, VerificationLog, VerificationResult
from app.schemas.schemas import VerifyResponse
from app.services.auth import decode_credential_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["verification"])


@router.get("/verify/{credential_token}", response_model=VerifyResponse)
async def verify_credential(
    credential_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify a media credential by its signed token (scanned from QR code)."""
    client_ip = request.client.host if request.client else "unknown"

    # Decode the token
    payload = decode_credential_token(credential_token)

    if payload is None:
        # Invalid / tampered token
        return VerifyResponse(
            valid=False,
            status="invalid",
            message="Invalid credential — QR code could not be verified.",
        )

    if payload.get("error") == "expired":
        # Token expired
        # Try to find credential for logging
        result = await db.execute(
            select(Credential).where(Credential.credential_token == credential_token)
        )
        cred = result.scalar_one_or_none()
        if cred:
            log = VerificationLog(
                credential_id=cred.id,
                scanned_by_ip=client_ip,
                result=VerificationResult.EXPIRED,
            )
            db.add(log)
            await db.flush()

        return VerifyResponse(
            valid=False,
            status="expired",
            message="This credential has expired.",
        )

    cred_id = payload.get("cred_id")
    if not cred_id:
        return VerifyResponse(
            valid=False,
            status="invalid",
            message="Invalid credential format.",
        )

    # Fetch credential with application
    result = await db.execute(
        select(Credential)
        .options(selectinload(Credential.application))
        .where(Credential.id == cred_id)
    )
    cred = result.scalar_one_or_none()

    if not cred:
        return VerifyResponse(
            valid=False,
            status="invalid",
            message="Credential not found.",
        )

    # Check if revoked
    if cred.is_revoked:
        log = VerificationLog(
            credential_id=cred.id,
            scanned_by_ip=client_ip,
            result=VerificationResult.REVOKED,
        )
        db.add(log)
        await db.flush()
        return VerifyResponse(
            valid=False,
            status="revoked",
            message="This credential has been revoked.",
        )

    # Check expiry
    now = datetime.now(timezone.utc)
    if cred.expires_at and cred.expires_at < now:
        log = VerificationLog(
            credential_id=cred.id,
            scanned_by_ip=client_ip,
            result=VerificationResult.EXPIRED,
        )
        db.add(log)
        await db.flush()
        return VerifyResponse(
            valid=False,
            status="expired",
            message="This credential has expired.",
        )

    # Valid credential
    app = cred.application
    log = VerificationLog(
        credential_id=cred.id,
        scanned_by_ip=client_ip,
        result=VerificationResult.VALID,
    )
    db.add(log)
    await db.flush()

    logger.info(f"Valid verification: {cred.badge_number} by {client_ip}")

    return VerifyResponse(
        valid=True,
        status="valid",
        full_name=app.full_name,
        organization=app.organization,
        designation=app.designation,
        media_type=app.media_type.value,
        face_photo_url=app.face_photo_url,
        badge_number=cred.badge_number,
        message="Credential verified — media personnel is authorized.",
    )
