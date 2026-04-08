"""OCR extraction service — extracts NIC number from ID document images."""
import io
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_id_info(image_bytes: bytes) -> dict:
    """Extract NIC number and name from an ID document image.

    Returns: {"id_number": str|None, "name": str|None, "confidence": "high"|"low"|None}
    """
    result = {"id_number": None, "name": None, "confidence": None}

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        logger.warning("pytesseract or PIL not available — OCR disabled")
        return result

    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")

        text = pytesseract.image_to_string(image)
        logger.debug(f"OCR raw text: {text[:200]}")

        # Extract NIC number — 12-digit new format or 9-digit + V/X old format
        new_nic = re.search(r'\b(\d{12})\b', text)
        if new_nic:
            result["id_number"] = new_nic.group(1)
            result["confidence"] = "high"
        else:
            old_nic = re.search(r'\b(\d{9}[VvXx])\b', text)
            if old_nic:
                result["id_number"] = old_nic.group(1).upper()
                result["confidence"] = "high"

        # Best-effort name extraction — grab the rest of the line after "Name:"
        # Clean OCR artifacts (pipes, brackets) that Tesseract sometimes produces
        name_match = re.search(r'(?:Name)\s*[:\-|]?\s*(.+)', text)
        if name_match:
            raw = name_match.group(1).strip()
            # Keep only letters, spaces, dots — remove pipes, digits, special chars
            name = re.sub(r'[^A-Za-z\s\.]', '', raw).strip()
            # Collapse multiple spaces
            name = re.sub(r'\s+', ' ', name)
            if len(name) >= 3:
                result["name"] = name.upper()
                if result["confidence"] is None:
                    result["confidence"] = "low"

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")

    return result
