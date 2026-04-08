"""Walk for Peace — Media Credential Management System."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db, async_session, clear_all_records
from app.services.auth import seed_admin

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Walk for Peace Media Credential System")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Create tables
    await init_db()
    logger.info("Database tables created/verified")

    # One-time cleanup: clear all test records
    await clear_all_records()

    # Seed admin
    async with async_session() as db:
        await seed_admin(db)

    # Ensure upload dir exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    yield

    await close_db()
    logger.info("Application shutdown")


app = FastAPI(
    title="Walk for Peace — Media Credentials",
    description="Media credential management for Walk for Peace Sri Lanka 2026",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — support multi-subdomain
allowed_origins = [
    "https://register.walkforpeacelk.org",
    "https://verify.walkforpeacelk.org",
    "https://admin.walkforpeacelk.org",
    "https://walkforpeacelk.org",
    "https://www.walkforpeacelk.org",
]
if settings.CORS_ORIGINS:
    allowed_origins.extend(settings.CORS_ORIGINS.split(","))
if settings.ENVIRONMENT == "development":
    allowed_origins.extend([
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
        "http://localhost:3000", "http://localhost:8000",
        "http://register.walkforpeacelk.com", "http://verify.walkforpeacelk.com",
        "http://admin.walkforpeacelk.com",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# Routes
from app.api.registration import router as registration_router
from app.api.admin import router as admin_router
from app.api.verification import router as verification_router
from app.api.verify_auth import router as verify_auth_router

app.include_router(registration_router)
app.include_router(admin_router)
app.include_router(verification_router)
app.include_router(verify_auth_router)

# Serve uploaded files (all environments — nginx proxies /uploads/ here)
uploads_path = Path(settings.UPLOAD_DIR)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "walkforpeace-api", "environment": settings.ENVIRONMENT}
