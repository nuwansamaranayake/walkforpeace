"""Application configuration from environment variables."""
import os
from pathlib import Path


class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://walkforpeace:walkforpeace@localhost:5432/walkforpeace",
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://walkforpeace:walkforpeace@localhost:5432/walkforpeace",
    )

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production-jwt-secret")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # QR Credential signing (separate from admin JWT)
    CREDENTIAL_SECRET: str = os.getenv(
        "CREDENTIAL_SECRET", "change-me-in-production-credential-secret"
    )
    # Credentials expire 2 days after event
    EVENT_DATE: str = os.getenv("EVENT_DATE", "2026-04-21")
    CREDENTIAL_EXPIRE_DAYS_AFTER_EVENT: int = 2

    # Cloudflare R2
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "walkforpeace-media")
    R2_PUBLIC_URL: str = os.getenv("R2_PUBLIC_URL", "")

    # File storage fallback (local filesystem when R2 not configured)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")

    # SMTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@walkforpeacelk.org")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Walk for Peace Sri Lanka")

    # App
    APP_URL: str = os.getenv("APP_URL", "https://walkforpeacelk.org")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Rate limiting
    RATE_LIMIT_REGISTRATIONS: int = int(
        os.getenv("RATE_LIMIT_REGISTRATIONS", "10")
    )  # per IP per hour

    # Face matching
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.60"))

    # Admin seed
    ADMIN_DEFAULT_USERNAME: str = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv(
        "ADMIN_DEFAULT_PASSWORD", "WalkForPeace2026!"
    )

    # Verify subdomain
    VERIFY_PASSWORD: str = os.getenv("VERIFY_PASSWORD", "Peace2026Verify")
    VERIFY_SESSION_HOURS: int = int(os.getenv("VERIFY_SESSION_HOURS", "24"))

    # CORS — explicit origin list for multi-subdomain
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    @property
    def use_r2(self) -> bool:
        return bool(self.R2_ENDPOINT_URL and self.R2_ACCESS_KEY_ID)


settings = Settings()
