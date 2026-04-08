"""Badge PDF generation for approved media personnel."""
import io
from typing import Optional

from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
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
    """Generate a printable badge PDF (A6 portrait) with large QR code."""
    buf = io.BytesIO()
    W, H = A6  # 105mm x 148mm portrait
    c = canvas.Canvas(buf, pagesize=A6)

    # Background
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top header bar
    header_h = 22 * mm
    c.setFillColor(NAVY)
    c.rect(0, H - header_h, W, header_h, fill=1, stroke=0)

    # Saffron accent line under header
    c.setFillColor(SAFFRON)
    c.rect(0, H - header_h - 1.5 * mm, W, 1.5 * mm, fill=1, stroke=0)

    # Header text
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W / 2, H - 9 * mm, "WALK FOR PEACE SRI LANKA 2026")
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, H - 14 * mm, "MEDIA CREDENTIAL")

    # Badge number in header
    c.setFillColor(SAFFRON)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(W / 2, H - 19 * mm, badge_number)

    # --- Content area ---
    content_top = H - header_h - 5 * mm
    cx = W / 2  # center x

    # Full name
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    # Truncate long names
    name_display = full_name if len(full_name) <= 25 else full_name[:23] + ".."
    c.drawCentredString(cx, content_top - 5 * mm, name_display)

    # Organization
    c.setFillColor(HexColor("#4A4A5A"))
    c.setFont("Helvetica", 9)
    org_display = organization if len(organization) <= 30 else organization[:28] + ".."
    c.drawCentredString(cx, content_top - 11 * mm, org_display)

    # Designation
    c.setFont("Helvetica", 8)
    c.drawCentredString(cx, content_top - 16 * mm, designation)

    # Media type badge
    mt_y = content_top - 23 * mm
    mt_text = media_type.upper()
    c.setFillColor(SAFFRON)
    text_w = c.stringWidth(mt_text, "Helvetica-Bold", 8) + 8 * mm
    p = c.beginPath()
    p.roundRect(cx - text_w / 2, mt_y - 1 * mm, text_w, 5 * mm, 2 * mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, mt_y + 0.5 * mm, mt_text)

    # --- Large QR code — fills remaining space ---
    qr_top = mt_y - 5 * mm
    bottom_bar_h = 8 * mm
    available_h = qr_top - bottom_bar_h - 3 * mm
    available_w = W - 12 * mm  # 6mm margin each side
    qr_size = min(available_h, available_w)

    try:
        qr_img = Image.open(io.BytesIO(qr_code_bytes))
        # Upscale for crisp print: target ~600px with NEAREST (no blur)
        qr_print_px = 600
        if qr_img.size[0] < qr_print_px:
            qr_img = qr_img.resize((qr_print_px, qr_print_px), Image.NEAREST)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        qr_reader = ImageReader(qr_buf)
        qr_x = (W - qr_size) / 2
        qr_y = qr_top - qr_size
        c.drawImage(qr_reader, qr_x, qr_y, qr_size, qr_size)
    except Exception:
        pass

    # Bottom bar
    c.setFillColor(NAVY)
    c.rect(0, 0, W, bottom_bar_h, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(W / 2, 2.5 * mm, "walkforpeacelk.org  |  April 21, 2026  |  Scan QR to verify")

    c.showPage()
    c.save()
    return buf.getvalue()
