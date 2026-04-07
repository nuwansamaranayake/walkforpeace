"""Badge PDF generation for approved media personnel."""
import io
import tempfile
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import A6, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image


SAFFRON = HexColor("#E8930A")
NAVY = HexColor("#1B2A4A")
GOLD = HexColor("#F5C563")
WHITE = white


def generate_badge_pdf(
    full_name: str,
    organization: str,
    designation: str,
    media_type: str,
    badge_number: str,
    face_photo_bytes: bytes,
    qr_code_bytes: bytes,
    logo_path: Optional[str] = None,
) -> bytes:
    """Generate a printable badge PDF (A6 landscape)."""
    buf = io.BytesIO()
    W, H = landscape(A6)  # ~148mm x 105mm
    c = canvas.Canvas(buf, pagesize=landscape(A6))

    # Background
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top header bar
    c.setFillColor(NAVY)
    c.rect(0, H - 28 * mm, W, 28 * mm, fill=1, stroke=0)

    # Saffron accent line
    c.setFillColor(SAFFRON)
    c.rect(0, H - 28.5 * mm, W, 1.5 * mm, fill=1, stroke=0)

    # Header text
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, H - 10 * mm, "WALK FOR PEACE SRI LANKA 2026")
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, H - 15 * mm, "MEDIA CREDENTIAL")

    # Badge number
    c.setFillColor(SAFFRON)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, H - 22 * mm, badge_number)

    # --- Content area ---
    content_top = H - 32 * mm

    # Face photo (left side)
    try:
        face_img = Image.open(io.BytesIO(face_photo_bytes))
        if face_img.mode in ("RGBA", "P"):
            face_img = face_img.convert("RGB")
        # Resize to passport size
        face_img = face_img.resize((120, 150), Image.LANCZOS)
        face_buf = io.BytesIO()
        face_img.save(face_buf, format="JPEG")
        face_buf.seek(0)
        face_reader = ImageReader(face_buf)
        photo_w = 28 * mm
        photo_h = 35 * mm
        photo_x = 8 * mm
        photo_y = content_top - photo_h - 3 * mm
        c.drawImage(face_reader, photo_x, photo_y, photo_w, photo_h)
        # Photo border
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.5)
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)
    except Exception:
        photo_x = 8 * mm
        photo_y = content_top - 35 * mm - 3 * mm
        pass

    # Person details (center)
    detail_x = 42 * mm
    detail_y = content_top - 8 * mm

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(detail_x, detail_y, full_name)

    detail_y -= 6 * mm
    c.setFillColor(HexColor("#4A4A5A"))
    c.setFont("Helvetica", 9)
    c.drawString(detail_x, detail_y, organization)

    detail_y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawString(detail_x, detail_y, designation)

    # Media type badge
    detail_y -= 7 * mm
    mt_text = media_type.upper()
    c.setFillColor(SAFFRON)
    text_w = c.stringWidth(mt_text, "Helvetica-Bold", 8) + 8 * mm
    p = c.beginPath()
    p.roundRect(detail_x, detail_y - 1 * mm, text_w, 5 * mm, 2 * mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(detail_x + 4 * mm, detail_y + 0.5 * mm, mt_text)

    # QR code (right side)
    try:
        qr_img = Image.open(io.BytesIO(qr_code_bytes))
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        qr_reader = ImageReader(qr_buf)
        qr_size = 28 * mm
        qr_x = W - qr_size - 8 * mm
        qr_y = content_top - qr_size - 5 * mm
        c.drawImage(qr_reader, qr_x, qr_y, qr_size, qr_size)
    except Exception:
        pass

    # Bottom bar
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 8 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 6)
    c.drawCentredString(W / 2, 2.5 * mm, "walkforpeacelk.org  •  April 21, 2026  •  Scan QR to verify")

    c.showPage()
    c.save()
    return buf.getvalue()
