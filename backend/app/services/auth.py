"""Authentication service — JWT tokens and password hashing."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import AdminUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_credential_token(credential_id: str, expires_at: datetime) -> str:
    """Create a signed token for QR code credential verification."""
    payload = {
        "cred_id": credential_id,
        "type": "credential",
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload, settings.CREDENTIAL_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def decode_credential_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.CREDENTIAL_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        return {"error": "expired"}
    except jwt.InvalidTokenError:
        return None


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[AdminUser]:
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == username)
    )
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        user.last_login = datetime.now(timezone.utc)
        await db.flush()
        return user
    return None


async def seed_admin(db: AsyncSession):
    """Seed default admin user if none exists."""
    result = await db.execute(select(AdminUser))
    if result.scalar_one_or_none() is None:
        admin = AdminUser(
            id=uuid.uuid4(),
            username=settings.ADMIN_DEFAULT_USERNAME,
            password_hash=hash_password(settings.ADMIN_DEFAULT_PASSWORD),
            must_change_password=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Seeded admin user: {settings.ADMIN_DEFAULT_USERNAME}")
