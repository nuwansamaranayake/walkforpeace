"""File storage service — Cloudflare R2 or local filesystem fallback."""
import os
import uuid
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from app.config import settings

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def validate_file(content_type: str, size: int) -> Optional[str]:
    """Returns error message or None if valid."""
    if content_type not in ALLOWED_TYPES:
        return f"Invalid file type: {content_type}. Allowed: {ALLOWED_TYPES}"
    if size > MAX_FILE_SIZE:
        return f"File too large: {size} bytes. Max: {MAX_FILE_SIZE} bytes (5MB)"
    return None


def generate_file_key(category: str, original_filename: str) -> str:
    ext = Path(original_filename).suffix or ".jpg"
    return f"{category}/{uuid.uuid4().hex}{ext}"


async def upload_file(file_bytes: bytes, file_key: str, content_type: str) -> str:
    """Upload file and return its URL."""
    if settings.use_r2:
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=file_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        if settings.R2_PUBLIC_URL:
            return f"{settings.R2_PUBLIC_URL}/{file_key}"
        return f"{settings.R2_ENDPOINT_URL}/{settings.R2_BUCKET_NAME}/{file_key}"
    else:
        # Local fallback
        local_path = Path(settings.UPLOAD_DIR) / file_key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return f"/uploads/{file_key}"


def get_presign_url(file_key: str, content_type: str, expires: int = 3600) -> str:
    """Generate a presigned upload URL for R2."""
    if not settings.use_r2:
        raise ValueError("R2 not configured — using direct upload")
    client = _get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": file_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )
