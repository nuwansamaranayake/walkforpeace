"""Admin dashboard API routes."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.config import settings
from app.database import get_db
from app.models.models import (
    AdminUser,
    ApplicationStatus,
    Credential,
    MediaApplication,
    MediaType,
)
from app.schemas.schemas import (
    ApplicationDetail,
    ApplicationListItem,
    ApplicationListResponse,
    ChangePasswordRequest,
    CredentialInfo,
    DashboardStats,
    LoginRequest,
    LoginResponse,
    ReviewRequest,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_credential_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.badge import generate_badge_pdf
from app.services.email import send_credential_email, send_rejection_email
from app.services.qr_service import generate_qr_code
from app.services.storage import upload_file, generate_file_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return LoginResponse(
        access_token=create_access_token(str(user.id), user.username),
        refresh_token=create_refresh_token(str(user.id)),
        must_change_password=user.must_change_password,
    )


@router.post("/refresh")
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    user_id = payload["sub"]
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")
    return {
        "access_token": create_access_token(str(user.id), user.username),
        "token_type": "bearer",
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, admin.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    admin.password_hash = hash_password(body.new_password)
    admin.must_change_password = False
    await db.flush()
    return {"message": "Password changed successfully"}


@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications(
    status: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    flagged: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(MediaApplication)
    count_query = select(func.count(MediaApplication.id))

    # Filters
    if status:
        try:
            s = ApplicationStatus(status)
            query = query.where(MediaApplication.status == s)
            count_query = count_query.where(MediaApplication.status == s)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    if media_type:
        try:
            mt = MediaType(media_type)
            query = query.where(MediaApplication.media_type == mt)
            count_query = count_query.where(MediaApplication.media_type == mt)
        except ValueError:
            raise HTTPException(400, f"Invalid media type: {media_type}")

    if flagged is not None:
        query = query.where(MediaApplication.face_match_flagged == flagged)
        count_query = count_query.where(
            MediaApplication.face_match_flagged == flagged
        )

    if search:
        search_filter = or_(
            MediaApplication.full_name.ilike(f"%{search}%"),
            MediaApplication.organization.ilike(f"%{search}%"),
            MediaApplication.ref_number.ilike(f"%{search}%"),
            MediaApplication.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginated results
    query = (
        query.order_by(MediaApplication.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return ApplicationListResponse(
        items=[
            ApplicationListItem(
                id=app.id,
                ref_number=app.ref_number,
                full_name=app.full_name,
                organization=app.organization,
                designation=app.designation,
                email=app.email,
                media_type=app.media_type.value,
                status=app.status.value,
                face_match_score=app.face_match_score,
                face_match_flagged=app.face_match_flagged,
                created_at=app.created_at,
            )
            for app in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/applications/{app_id}", response_model=ApplicationDetail)
async def get_application(
    app_id: uuid.UUID,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MediaApplication)
        .options(selectinload(MediaApplication.credential))
        .where(MediaApplication.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")

    cred_info = None
    if app.credential:
        cred_info = CredentialInfo(
            id=app.credential.id,
            credential_token=app.credential.credential_token,
            qr_code_url=app.credential.qr_code_url,
            badge_pdf_url=app.credential.badge_pdf_url,
            badge_number=app.credential.badge_number,
            issued_at=app.credential.issued_at,
            expires_at=app.credential.expires_at,
            is_revoked=app.credential.is_revoked,
        )

    return ApplicationDetail(
        id=app.id,
        ref_number=app.ref_number,
        full_name=app.full_name,
        organization=app.organization,
        designation=app.designation,
        email=app.email,
        phone=app.phone,
        country=app.country,
        media_type=app.media_type.value,
        status=app.status.value,
        id_document_url=app.id_document_url,
        id_face_crop_url=app.id_face_crop_url,
        face_photo_url=app.face_photo_url,
        face_match_score=app.face_match_score,
        face_match_flagged=app.face_match_flagged,
        admin_notes=app.admin_notes,
        reviewed_at=app.reviewed_at,
        reviewed_by=app.reviewed_by,
        created_at=app.created_at,
        updated_at=app.updated_at,
        credential=cred_info,
    )


@router.patch("/applications/{app_id}/review")
async def review_application(
    app_id: uuid.UUID,
    body: ReviewRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MediaApplication).where(MediaApplication.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")

    if app.status != ApplicationStatus.PENDING:
        raise HTTPException(400, f"Application already {app.status.value}")

    now = datetime.now(timezone.utc)
    app.reviewed_by = admin.id
    app.reviewed_at = now
    app.admin_notes = body.admin_notes
    app.updated_at = now

    if body.action == "approve":
        app.status = ApplicationStatus.APPROVED

        # Generate credential
        event_date = datetime.strptime(settings.EVENT_DATE, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        expires_at = event_date + timedelta(
            days=settings.CREDENTIAL_EXPIRE_DAYS_AFTER_EVENT
        )

        cred_id = uuid.uuid4()
        badge_number = f"WFP-{str(cred_id.hex[:6]).upper()}"
        credential_token = create_credential_token(str(cred_id), expires_at)

        # Generate QR code
        qr_bytes = generate_qr_code(credential_token)
        qr_key = generate_file_key("qr-codes", f"{badge_number}.png")
        qr_url = await upload_file(qr_bytes, qr_key, "image/png")

        # Generate badge PDF — need face photo bytes
        # Fetch face photo from storage
        try:
            import httpx, aiofiles
            from pathlib import Path

            face_bytes = b""
            if app.face_photo_url.startswith("/uploads/"):
                local_path = Path(settings.UPLOAD_DIR) / app.face_photo_url.replace(
                    "/uploads/", ""
                )
                if local_path.exists():
                    with open(local_path, "rb") as f:
                        face_bytes = f.read()
            elif app.face_photo_url.startswith("http"):
                async with httpx.AsyncClient() as client:
                    resp = await client.get(app.face_photo_url)
                    face_bytes = resp.content

            badge_bytes = generate_badge_pdf(
                full_name=app.full_name,
                organization=app.organization,
                designation=app.designation,
                media_type=app.media_type.value,
                badge_number=badge_number,
                face_photo_bytes=face_bytes,
                qr_code_bytes=qr_bytes,
            )
            badge_key = generate_file_key("badges", f"{badge_number}.pdf")
            badge_url = await upload_file(badge_bytes, badge_key, "application/pdf")
        except Exception as e:
            logger.error(f"Badge generation failed: {e}")
            badge_url = None
            badge_bytes = b""

        credential = Credential(
            id=cred_id,
            application_id=app.id,
            credential_token=credential_token,
            qr_code_url=qr_url,
            badge_pdf_url=badge_url,
            badge_number=badge_number,
            expires_at=expires_at,
        )
        db.add(credential)
        await db.flush()

        # Send credential email
        try:
            send_credential_email(
                app.email, app.full_name, badge_number, qr_bytes, badge_bytes
            )
        except Exception as e:
            logger.error(f"Failed to send credential email: {e}")

        return {
            "message": "Application approved",
            "badge_number": badge_number,
            "credential_token": credential_token,
        }

    elif body.action == "reject":
        app.status = ApplicationStatus.REJECTED
        await db.flush()

        try:
            send_rejection_email(
                app.email, app.full_name, app.ref_number, body.admin_notes or ""
            )
        except Exception as e:
            logger.error(f"Failed to send rejection email: {e}")

        return {"message": "Application rejected"}


@router.post("/applications/{app_id}/revoke")
async def revoke_credential(
    app_id: uuid.UUID,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Credential).where(Credential.application_id == app_id)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(404, "Credential not found")
    cred.is_revoked = True
    await db.flush()
    return {"message": "Credential revoked"}


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(select(func.count(MediaApplication.id)))
    ).scalar()
    pending = (
        await db.execute(
            select(func.count(MediaApplication.id)).where(
                MediaApplication.status == ApplicationStatus.PENDING
            )
        )
    ).scalar()
    approved = (
        await db.execute(
            select(func.count(MediaApplication.id)).where(
                MediaApplication.status == ApplicationStatus.APPROVED
            )
        )
    ).scalar()
    rejected = (
        await db.execute(
            select(func.count(MediaApplication.id)).where(
                MediaApplication.status == ApplicationStatus.REJECTED
            )
        )
    ).scalar()
    flagged = (
        await db.execute(
            select(func.count(MediaApplication.id)).where(
                MediaApplication.face_match_flagged == True
            )
        )
    ).scalar()
    creds = (
        await db.execute(select(func.count(Credential.id)))
    ).scalar()

    return DashboardStats(
        total_registered=total or 0,
        pending=pending or 0,
        approved=approved or 0,
        rejected=rejected or 0,
        flagged_face_match=flagged or 0,
        credentials_issued=creds or 0,
    )
