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


async def close_db():
    await engine.dispose()
