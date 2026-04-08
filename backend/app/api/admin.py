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
    VerificationLog,
)
from app.models.verify_session import VerifySession
from app.schemas.schemas import (
    ApplicationDetail,
    ApplicationListItem,
    ApplicationListResponse,
    BatchApproveRequest,
    BatchApproveResponse,
    ChangePasswordRequest,
    CredentialInfo,
    DashboardStats,
    GatekeeperInfo,
    LoginRequest,
    LoginResponse,
    ReviewRequest,
    ScanActivityItem,
    ScanLogItem,
    VerificationLogItem,
    VerificationLogResponse,
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
                pin_code=app.pin_code,
                id_number=app.id_number,
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
            verification_status=app.credential.verification_status,
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
        id_number=app.id_number,
        id_type=app.id_type,
        ocr_extracted_name=app.ocr_extracted_name,
        ocr_extracted_id=app.ocr_extracted_id,
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

        # Credential already exists from registration — update its verification_status
        result2 = await db.execute(
            select(Credential).where(Credential.application_id == app.id)
        )
        cred = result2.scalar_one_or_none()
        if not cred:
            raise HTTPException(500, "Credential missing — should have been created at registration")

        cred.verification_status = "approved"

        # Generate badge PDF if not already generated
        if not cred.badge_pdf_url:
            try:
                import httpx
                from pathlib import Path

                face_bytes = b""
                if app.face_photo_url.startswith("/uploads/"):
                    local_path = Path(settings.UPLOAD_DIR) / app.face_photo_url.replace("/uploads/", "")
                    if local_path.exists():
                        with open(local_path, "rb") as f:
                            face_bytes = f.read()
                elif app.face_photo_url.startswith("http"):
                    async with httpx.AsyncClient() as hclient:
                        resp = await hclient.get(app.face_photo_url)
                        face_bytes = resp.content

                qr_bytes = generate_qr_code(cred.credential_token)
                badge_bytes = generate_badge_pdf(
                    full_name=app.full_name,
                    organization=app.organization,
                    designation=app.designation,
                    media_type=app.media_type.value,
                    badge_number=cred.badge_number,
                    face_photo_bytes=face_bytes,
                    qr_code_bytes=qr_bytes,
                )
                badge_key = generate_file_key("badges", f"{cred.badge_number}.pdf")
                cred.badge_pdf_url = await upload_file(badge_bytes, badge_key, "application/pdf")
            except Exception as e:
                logger.error(f"Badge generation failed: {e}")

        # Send credential email
        try:
            send_credential_email(
                app.email, app.full_name, cred.badge_number,
                qr_bytes if 'qr_bytes' in dir() else b"",
                badge_bytes if 'badge_bytes' in dir() else b"",
            )
        except Exception as e:
            logger.error(f"Failed to send credential email: {e}")

        await db.flush()
        return {
            "message": "Application approved",
            "badge_number": cred.badge_number,
            "credential_token": cred.credential_token,
        }

    elif body.action == "reject":
        app.status = ApplicationStatus.REJECTED

        result2 = await db.execute(
            select(Credential).where(Credential.application_id == app.id)
        )
        cred = result2.scalar_one_or_none()
        if cred:
            cred.verification_status = "rejected"

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
    cred.verification_status = "revoked"
    await db.flush()
    return {"message": "Credential revoked"}


@router.post("/applications/batch-approve", response_model=BatchApproveResponse)
async def batch_approve(
    body: BatchApproveRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve multiple pending applications at once."""
    approved_count = 0
    now = datetime.now(timezone.utc)

    for app_id_str in body.application_ids:
        try:
            app_id = uuid.UUID(app_id_str)
        except ValueError:
            continue

        result = await db.execute(
            select(MediaApplication).where(MediaApplication.id == app_id)
        )
        app = result.scalar_one_or_none()
        if not app or app.status != ApplicationStatus.PENDING:
            continue

        app.status = ApplicationStatus.APPROVED
        app.reviewed_by = admin.id
        app.reviewed_at = now
        app.updated_at = now

        cred_result = await db.execute(
            select(Credential).where(Credential.application_id == app.id)
        )
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred.verification_status = "approved"

        approved_count += 1

    await db.flush()
    return BatchApproveResponse(
        approved_count=approved_count,
        message=f"Approved {approved_count} application(s)",
    )


@router.get("/verification-logs", response_model=VerificationLogResponse)
async def list_verification_logs(
    credential_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List verification scan logs with optional filters."""
    query = select(VerificationLog).options(
        selectinload(VerificationLog.credential).selectinload(Credential.application)
    )
    count_query = select(func.count(VerificationLog.id))

    if credential_id:
        try:
            cid = uuid.UUID(credential_id)
            query = query.where(VerificationLog.credential_id == cid)
            count_query = count_query.where(VerificationLog.credential_id == cid)
        except ValueError:
            raise HTTPException(400, "Invalid credential_id format")

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(VerificationLog.scanned_at >= dt_from)
            count_query = count_query.where(VerificationLog.scanned_at >= dt_from)
        except ValueError:
            raise HTTPException(400, "Invalid date_from format (use ISO 8601)")

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(VerificationLog.scanned_at <= dt_to)
            count_query = count_query.where(VerificationLog.scanned_at <= dt_to)
        except ValueError:
            raise HTTPException(400, "Invalid date_to format (use ISO 8601)")

    total = (await db.execute(count_query)).scalar() or 0

    query = (
        query.order_by(VerificationLog.scanned_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    items = []
    for log in logs:
        cred = log.credential
        app_obj = cred.application if cred else None
        items.append(VerificationLogItem(
            id=log.id,
            credential_id=log.credential_id,
            badge_number=cred.badge_number if cred else None,
            full_name=app_obj.full_name if app_obj else None,
            scanned_at=log.scanned_at,
            scanned_by_ip=log.scanned_by_ip,
            result=log.result.value,
            verified_by_action=log.verified_by_action,
        ))

    return VerificationLogResponse(
        items=items, total=total, page=page, page_size=page_size,
    )


@router.get("/applications/{app_id}/scans", response_model=list[ScanLogItem])
async def get_application_scans(
    app_id: uuid.UUID,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all scan logs for a specific application."""
    # Find the credential for this application
    cred_result = await db.execute(
        select(Credential).where(Credential.application_id == app_id)
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        return []

    result = await db.execute(
        select(VerificationLog)
        .where(VerificationLog.credential_id == cred.id)
        .order_by(VerificationLog.scanned_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()

    return [
        ScanLogItem(
            id=log.id,
            scanned_at=log.scanned_at,
            scanned_by_ip=log.scanned_by_ip,
            result=log.result.value,
            verified_by_action=log.verified_by_action,
            latitude=log.latitude,
            longitude=log.longitude,
            place_name=log.place_name,
            device_id=log.device_id,
        )
        for log in logs
    ]


@router.get("/gatekeepers", response_model=list[GatekeeperInfo])
async def list_gatekeepers(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all verify sessions with device info and scan counts."""
    now = datetime.now(timezone.utc)
    ten_min_ago = now - timedelta(minutes=10)

    twenty_four_hours_ago = now - timedelta(hours=24)
    result = await db.execute(
        select(VerifySession)
        .where(VerifySession.is_expired == False)
        .where(VerifySession.expires_at > now)
        .where(
            # Only show sessions that have scanned OR have device info (v3+)
            (VerifySession.total_scans > 0) | (VerifySession.device_name.isnot(None))
        )
        .order_by(VerifySession.last_scan_at.desc().nullslast())
        .limit(50)
    )
    sessions = result.scalars().all()

    return [
        GatekeeperInfo(
            id=s.id,
            device_name=s.device_name or (s.device_info[:60] + "..." if s.device_info and len(s.device_info) > 60 else s.device_info),
            device_ip=s.device_ip,
            screen_size=s.screen_size,
            total_scans=s.total_scans or 0,
            last_scan_at=s.last_scan_at,
            last_location=s.last_location,
            created_at=s.created_at,
            status="active" if s.last_scan_at and s.last_scan_at > ten_min_ago else "inactive",
        )
        for s in sessions
    ]


@router.get("/scan-activity")
async def list_scan_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Global scan activity feed for dashboard."""
    # Count total
    total = (
        await db.execute(select(func.count(VerificationLog.id)))
    ).scalar() or 0

    # Fetch logs with credential -> application join
    result = await db.execute(
        select(VerificationLog)
        .options(selectinload(VerificationLog.credential).selectinload(Credential.application))
        .order_by(VerificationLog.scanned_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = result.scalars().all()

    items = []
    for log in logs:
        full_name = None
        badge_number = None
        if log.credential:
            badge_number = log.credential.badge_number
            if log.credential.application:
                full_name = log.credential.application.full_name
        items.append(ScanActivityItem(
            id=log.id,
            scanned_at=log.scanned_at,
            full_name=full_name,
            badge_number=badge_number,
            result=log.result.value,
            verified_by_action=log.verified_by_action,
            place_name=log.place_name,
            device_id=log.device_id,
            scanned_by_ip=log.scanned_by_ip,
        ))

    return {"items": items, "total": total, "page": page, "page_size": page_size}


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

    # Total scans today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    scans_today = (
        await db.execute(
            select(func.count(VerificationLog.id)).where(
                VerificationLog.scanned_at >= today_start
            )
        )
    ).scalar()

    # Active gatekeepers (sessions with scan in last 10 min)
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    active_gk = (
        await db.execute(
            select(func.count(VerifySession.id)).where(
                VerifySession.is_expired == False,
                VerifySession.expires_at > datetime.now(timezone.utc),
                VerifySession.last_scan_at > ten_min_ago,
            )
        )
    ).scalar()

    return DashboardStats(
        total_registered=total or 0,
        pending=pending or 0,
        approved=approved or 0,
        rejected=rejected or 0,
        flagged=flagged or 0,
        credentials_issued=creds or 0,
        total_scans_today=scans_today or 0,
        active_gatekeepers=active_gk or 0,
    )
