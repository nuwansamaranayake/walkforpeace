"""Auth dependencies for FastAPI routes."""
from typing import Optional
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import AdminUser
from app.models.verify_session import VerifySession
from app.services.auth import decode_token

bearer_scheme = HTTPBearer()

# Optional bearer scheme — doesn't auto-error on missing token
optional_bearer = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_verify_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[VerifySession]:
    """Get verify session if valid token provided. Returns None if no/invalid token."""
    if not credentials:
        return None
    token = credentials.credentials
    result = await db.execute(
        select(VerifySession).where(VerifySession.session_token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    if session.expires_at < datetime.now(timezone.utc):
        return None
    return session


async def require_verify_session(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> VerifySession:
    """Require a valid verify session — 401 if missing or expired."""
    token = credentials.credentials
    result = await db.execute(
        select(VerifySession).where(VerifySession.session_token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid verify session")
    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Verify session expired")
    return session
