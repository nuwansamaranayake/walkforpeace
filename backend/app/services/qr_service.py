"""QR code generation for credentials."""
import io
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask

from app.config import settings


def generate_qr_code(credential_token: str) -> bytes:
    """Generate a QR code image (PNG bytes) for the credential verification URL."""
    verify_url = f"{settings.APP_URL}/api/verify/{credential_token}"

    qr = qrcode.QRCode(
        version=None,  # Auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=SolidFillColorMask(
            back_color=(255, 255, 255),
            front_color=(27, 42, 74),  # Navy
        ),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
