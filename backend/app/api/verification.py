"""Public verification API — QR code scanning + gate actions for security officers."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_verify_session, require_verify_session
from app.database import get_db
from app.models.models import Credential, MediaApplication, VerificationLog, VerificationResult
from app.models.verify_session import VerifySession
from app.schemas.schemas import VerifyResponseV2
from app.services.auth import decode_credential_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["verification"])


@router.get("/verify/{credential_token}", response_model=VerifyResponseV2)
async def verify_credential(
    credential_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session: Optional[VerifySession] = Depends(get_verify_session),
):
    """Verify a media credential. Response depth depends on verify session."""
    client_ip = request.client.host if request.client else "unknown"

    payload = decode_credential_token(credential_token)

    if payload is None:
        return VerifyResponseV2(
            valid=False, status="invalid",
            message="Invalid credential — QR code could not be verified.",
        )

    if payload.get("error") == "expired":
        result = await db.execute(
            select(Credential).where(Credential.credential_token == credential_token)
        )
        cred = result.scalar_one_or_none()
        if cred:
            db.add(VerificationLog(
                credential_id=cred.id, scanned_by_ip=client_ip,
                result=VerificationResult.EXPIRED,
            ))
            await db.flush()
        return VerifyResponseV2(
            valid=False, status="expired",
            message="This credential has expired.",
        )

    cred_id = payload.get("cred_id")
    if not cred_id:
        return VerifyResponseV2(
            valid=False, status="invalid",
            message="Invalid credential format.",
        )

    result = await db.execute(
        select(Credential)
        .options(selectinload(Credential.application))
        .where(Credential.id == cred_id)
    )
    cred = result.scalar_one_or_none()

    if not cred:
        return VerifyResponseV2(
            valid=False, status="invalid",
            message="Credential not found.",
        )

    app = cred.application
    vs = cred.verification_status

    if vs == "revoked" or cred.is_revoked:
        db.add(VerificationLog(
            credential_id=cred.id, scanned_by_ip=client_ip,
            result=VerificationResult.REVOKED,
        ))
        await db.flush()
        return VerifyResponseV2(
            valid=False, status="revoked",
            message="This credential has been revoked.",
        )

    now = datetime.now(timezone.utc)
    if cred.expires_at and cred.expires_at < now:
        db.add(VerificationLog(
            credential_id=cred.id, scanned_by_ip=client_ip,
            result=VerificationResult.EXPIRED,
        ))
        await db.flush()
        return VerifyResponseV2(
            valid=False, status="expired",
            message="This credential has expired.",
        )

    if vs == "rejected":
        log_result = VerificationResult.INVALID
    else:
        log_result = VerificationResult.VALID

    db.add(VerificationLog(
        credential_id=cred.id, scanned_by_ip=client_ip,
        result=log_result,
    ))
    await db.flush()

    messages = {
        "approved": "Credential verified — media personnel is authorized.",
        "pending": "Credential pending review — not yet approved.",
        "flagged": "Face match flagged — manual identity check required.",
        "rejected": "This credential application was rejected.",
    }

    is_valid = vs == "approved"

    response = VerifyResponseV2(
        valid=is_valid,
        status=vs,
        verification_status=vs,
        full_name=app.full_name,
        organization=app.organization,
        designation=app.designation,
        media_type=app.media_type.value,
        face_photo_url=app.face_photo_url,
        badge_number=cred.badge_number,
        message=messages.get(vs, "Unknown status"),
    )

    # Include sensitive fields only with valid verify session
    if session:
        response.can_gate_approve = (vs == "flagged")

    return response


@router.post("/verify/{credential_token}/gate-approve")
async def gate_approve(
    credential_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session: VerifySession = Depends(require_verify_session),
):
    """Security officer approves a flagged credential at the gate."""
    client_ip = request.client.host if request.client else "unknown"

    payload = decode_credential_token(credential_token)
    if not payload or payload.get("error"):
        raise HTTPException(400, "Invalid credential token")

    result = await db.execute(
        select(Credential).where(Credential.id == payload.get("cred_id"))
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(404, "Credential not found")

    if cred.verification_status != "flagged":
        raise HTTPException(400, f"Cannot gate-approve — status is '{cred.verification_status}', not 'flagged'")

    cred.verification_status = "approved"
    db.add(VerificationLog(
        credential_id=cred.id, scanned_by_ip=client_ip,
        result=VerificationResult.VALID,
        verified_by_action="gate_approved",
    ))
    await db.flush()

    logger.info(f"Gate-approved: {cred.badge_number} by {client_ip}")
    return {"message": "Credential gate-approved", "badge_number": cred.badge_number}


@router.post("/verify/{credential_token}/gate-deny")
async def gate_deny(
    credential_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session: VerifySession = Depends(require_verify_session),
):
    """Security officer denies a flagged credential at the gate."""
    client_ip = request.client.host if request.client else "unknown"

    payload = decode_credential_token(credential_token)
    if not payload or payload.get("error"):
        raise HTTPException(400, "Invalid credential token")

    result = await db.execute(
        select(Credential).where(Credential.id == payload.get("cred_id"))
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(404, "Credential not found")

    db.add(VerificationLog(
        credential_id=cred.id, scanned_by_ip=client_ip,
        result=VerificationResult.INVALID,
        verified_by_action="gate_denied",
    ))
    await db.flush()

    logger.info(f"Gate-denied: {cred.badge_number} by {client_ip}")
    return {"message": "Credential gate-denied — admin notified", "badge_number": cred.badge_number}
