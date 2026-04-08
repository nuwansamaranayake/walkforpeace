"""Async database session management."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine, text
from app.config import settings
from app.models.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for migrations and seeding
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=settings.DEBUG)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables and run schema migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Idempotent schema fixes for existing databases
    async with engine.begin() as conn:
        try:
            await conn.execute(text(
                "ALTER TABLE media_applications ALTER COLUMN id_face_crop_url DROP NOT NULL"
            ))
            logger.info("Made id_face_crop_url nullable")
        except Exception:
            pass  # Already nullable or column doesn't exist

    # v3: Add GPS + device columns to verification_logs
    async with engine.begin() as conn:
        migrations = [
            # verification_logs — GPS tracking
            "ALTER TABLE verification_logs ADD COLUMN IF NOT EXISTS latitude FLOAT",
            "ALTER TABLE verification_logs ADD COLUMN IF NOT EXISTS longitude FLOAT",
            "ALTER TABLE verification_logs ADD COLUMN IF NOT EXISTS place_name VARCHAR(200)",
            "ALTER TABLE verification_logs ADD COLUMN IF NOT EXISTS device_id VARCHAR(100)",
            "ALTER TABLE verification_logs ADD COLUMN IF NOT EXISTS verify_session_id UUID",
            # verify_sessions — logout flag
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS is_expired BOOLEAN NOT NULL DEFAULT false",
            # verify_sessions — device info + scan tracking
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS device_info VARCHAR(500)",
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS device_name VARCHAR(100)",
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS screen_size VARCHAR(20)",
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS total_scans INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS last_scan_at TIMESTAMPTZ",
            "ALTER TABLE verify_sessions ADD COLUMN IF NOT EXISTS last_location VARCHAR(200)",
        ]
        for sql in migrations:
            try:
                await conn.execute(text(sql))
            except Exception as e:
                logger.debug(f"Migration skipped (likely already applied): {e}")
        logger.info("v3 schema migrations applied")


async def clear_all_records():
    """Delete all application, credential, and verification records."""
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM verification_logs"))
        await conn.execute(text("DELETE FROM credentials"))
        await conn.execute(text("DELETE FROM media_applications"))
        logger.info("Cleared all application/credential records")


async def close_db():
    await engine.dispose()
