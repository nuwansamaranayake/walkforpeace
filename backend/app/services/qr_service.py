"""QR code generation for credentials."""
import io
import qrcode
from PIL import Image as PILImage

from app.config import settings

# Verify URL base — use the verify subdomain
VERIFY_BASE = settings.APP_URL.replace("register.", "verify.")


def generate_qr_code(credential_token: str) -> bytes:
    """Generate a QR code image (PNG bytes) for the credential verification URL.

    Optimised for reliable scanning when printed on badge PDFs:
    - ERROR_CORRECT_M balances density vs resilience for 200+ char URLs
    - box_size=12 produces a large source image (~500px+) for crisp PDF embedding
    - Plain PIL image (no StyledPilImage) avoids anti-aliasing artefacts
    """
    verify_url = f"{VERIFY_BASE}/api/verify/{credential_token}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=3,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    # Use plain PilImage — StyledPilImage introduces anti-aliasing that
    # blurs module edges and hurts scanning at small print sizes.
    # Use pure black for maximum contrast — navy fill caused scan failures
    # on many phone cameras.
    img = qr.make_image(fill_color=(0, 0, 0), back_color=(255, 255, 255))

    # Ensure crisp pixel-perfect output — resize with NEAREST to avoid blurring
    target = max(600, img.size[0])
    if img.size[0] < target:
        img = img.resize((target, target), PILImage.NEAREST)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
