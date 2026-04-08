"""Verify subdomain authentication — shared password, anonymous sessions."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.config import settings
from app.database import get_db
from app.models.verify_session import VerifySession
from app.schemas.schemas import VerifyAuthRequestV2, VerifyAuthResponse
from app.api.deps import require_verify_session

router = APIRouter(prefix="/api/verify", tags=["verify-auth"])


@router.post("/auth", response_model=VerifyAuthResponse)
async def verify_login(
    body: VerifyAuthRequestV2,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with the shared event-day password."""
    if body.password != settings.VERIFY_PASSWORD:
        raise HTTPException(401, "Invalid verification password")

    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.VERIFY_SESSION_HOURS)
    session_token = secrets.token_urlsafe(48)

    session = VerifySession(
        id=uuid.uuid4(),
        session_token=session_token,
        expires_at=expires_at,
        device_ip=client_ip,
        device_info=body.device_info,
        device_name=body.device_name,
        screen_size=body.screen_size,
    )
    db.add(session)
    await db.flush()

    return VerifyAuthResponse(
        session_token=session_token,
        expires_at=expires_at,
    )


@router.post("/logout")
async def verify_logout(
    db: AsyncSession = Depends(get_db),
    session: VerifySession = Depends(require_verify_session),
):
    """Invalidate the verify session (manual logout or inactivity timeout)."""
    session.is_expired = True
    await db.flush()
    return {"message": "Session invalidated"}
