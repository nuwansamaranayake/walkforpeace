"""Email service for registration confirmation and credential delivery."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.config import settings

logger = logging.getLogger(__name__)


def _get_smtp():
    """Create SMTP connection."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured — emails will be logged only")
        return None
    try:
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        return smtp
    except Exception as e:
        logger.error(f"SMTP connection failed: {e}")
        return None


def send_registration_confirmation(email: str, full_name: str, ref_number: str):
    """Send registration confirmation email."""
    subject = f"Walk for Peace — Registration Received ({ref_number})"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1B2A4A; padding: 20px; text-align: center;">
            <h1 style="color: #E8930A; margin: 0;">Walk for Peace Sri Lanka</h1>
            <p style="color: #F5C563; margin: 5px 0 0;">Media Credential System</p>
        </div>
        <div style="padding: 25px; background: #f9f9f9;">
            <p>Dear <strong>{full_name}</strong>,</p>
            <p>Thank you for registering for media credentials for the Walk for Peace Sri Lanka 2026.</p>
            <p>Your application has been received and is under review.</p>
            <div style="background: #fff; border-left: 4px solid #E8930A; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Reference Number:</strong> {ref_number}</p>
                <p style="margin: 5px 0 0;">You can check your status at: {settings.APP_URL}/status/{ref_number}</p>
            </div>
            <p>You will be notified once your application has been reviewed.</p>
            <p style="color: #666;">— Walk for Peace Media Team</p>
        </div>
        <div style="background: #1B2A4A; padding: 10px; text-align: center;">
            <p style="color: #F5C563; margin: 0; font-size: 12px;">April 21, 2026 • walkforpeacelk.org</p>
        </div>
    </div>
    """
    _send_email(email, subject, html)


def send_credential_email(
    email: str,
    full_name: str,
    badge_number: str,
    qr_code_bytes: bytes,
    badge_pdf_bytes: bytes,
):
    """Send approved credential with QR code and badge PDF."""
    subject = f"Walk for Peace — Your Media Credential ({badge_number})"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1B2A4A; padding: 20px; text-align: center;">
            <h1 style="color: #E8930A; margin: 0;">Walk for Peace Sri Lanka</h1>
            <p style="color: #F5C563; margin: 5px 0 0;">Media Credential Approved</p>
        </div>
        <div style="padding: 25px; background: #f9f9f9;">
            <p>Dear <strong>{full_name}</strong>,</p>
            <p>Your media credential for Walk for Peace Sri Lanka 2026 has been <strong style="color: #22C55E;">APPROVED</strong>.</p>
            <div style="background: #fff; border-left: 4px solid #22C55E; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Badge Number:</strong> {badge_number}</p>
                <p style="margin: 5px 0 0;">Your QR code and printable badge are attached to this email.</p>
            </div>
            <p><strong>On event day:</strong></p>
            <ul>
                <li>Show your QR code (from phone or printed badge) to security</li>
                <li>They will scan it to verify your credential</li>
                <li>Keep your ID document with you</li>
            </ul>
            <p style="color: #666;">— Walk for Peace Media Team</p>
        </div>
        <div style="background: #1B2A4A; padding: 10px; text-align: center;">
            <p style="color: #F5C563; margin: 0; font-size: 12px;">April 21, 2026 • walkforpeacelk.org</p>
        </div>
    </div>
    """
    _send_email(
        email,
        subject,
        html,
        attachments=[
            ("qr-code.png", qr_code_bytes, "image/png"),
            ("media-badge.pdf", badge_pdf_bytes, "application/pdf"),
        ],
    )


def send_rejection_email(email: str, full_name: str, ref_number: str, notes: str = ""):
    """Send rejection notification."""
    notes_html = f"<p><strong>Notes:</strong> {notes}</p>" if notes else ""
    subject = f"Walk for Peace — Application Update ({ref_number})"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1B2A4A; padding: 20px; text-align: center;">
            <h1 style="color: #E8930A; margin: 0;">Walk for Peace Sri Lanka</h1>
            <p style="color: #F5C563; margin: 5px 0 0;">Application Update</p>
        </div>
        <div style="padding: 25px; background: #f9f9f9;">
            <p>Dear <strong>{full_name}</strong>,</p>
            <p>We regret to inform you that your media credential application ({ref_number}) was not approved at this time.</p>
            {notes_html}
            <p>If you believe this is an error, please contact the media team.</p>
            <p style="color: #666;">— Walk for Peace Media Team</p>
        </div>
    </div>
    """
    _send_email(email, subject, html)


def _send_email(
    to: str, subject: str, html: str, attachments: list = None
):
    """Internal email sender."""
    logger.info(f"Sending email to {to}: {subject}")

    msg = MIMEMultipart()
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    if attachments:
        for filename, data, mime_type in attachments:
            part = MIMEBase(*mime_type.split("/"))
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

    smtp = _get_smtp()
    if smtp:
        try:
            smtp.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
            smtp.quit()
            logger.info(f"Email sent to {to}")
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
    else:
        logger.info(f"[DEV] Email would be sent to {to}: {subject}")
