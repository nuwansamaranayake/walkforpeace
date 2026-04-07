"""Face matching service using DeepFace with ArcFace model."""
import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy load DeepFace to avoid slow startup
_deepface = None


def _get_deepface():
    global _deepface
    if _deepface is None:
        try:
            from deepface import DeepFace

            _deepface = DeepFace
            logger.info("DeepFace loaded successfully")
        except ImportError:
            logger.warning("DeepFace not installed — face matching disabled")
    return _deepface


async def compute_face_match(
    id_face_bytes: bytes, live_photo_bytes: bytes
) -> Tuple[Optional[float], bool]:
    """
    Compare the ID face crop with the live face photo.

    Returns:
        (score, flagged) — score is 0.0-1.0 similarity, flagged=True if below threshold.
        Returns (None, False) if matching fails.
    """
    DeepFace = _get_deepface()
    if DeepFace is None:
        logger.warning("DeepFace unavailable, skipping face match")
        return None, False

    try:
        id_path = None
        live_path = None

        # Save to temp files (DeepFace needs file paths or numpy arrays)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f1:
            f1.write(_ensure_jpeg(id_face_bytes))
            id_path = f1.name

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f2:
            f2.write(_ensure_jpeg(live_photo_bytes))
            live_path = f2.name

        # Use ArcFace model — best accuracy for this use case
        result = DeepFace.verify(
            img1_path=id_path,
            img2_path=live_path,
            model_name="ArcFace",
            detector_backend="opencv",
            enforce_detection=False,  # Don't fail if face not detected clearly
        )

        # DeepFace returns distance (lower = more similar)
        # Convert to similarity score (0-1 range)
        distance = result.get("distance", 1.0)
        threshold = result.get("threshold", 0.68)

        # Normalize: score = 1 - (distance / (2 * threshold))
        # This gives ~0.5 at threshold, >0.5 for matches, <0.5 for non-matches
        score = max(0.0, min(1.0, 1.0 - (distance / (2 * threshold))))

        flagged = score < settings.FACE_MATCH_THRESHOLD

        logger.info(
            f"Face match: distance={distance:.3f}, threshold={threshold:.3f}, "
            f"score={score:.3f}, flagged={flagged}"
        )

        # Cleanup temp files
        Path(id_path).unlink(missing_ok=True)
        Path(live_path).unlink(missing_ok=True)

        return round(score, 3), flagged

    except Exception as e:
        logger.error(f"Face matching failed: {e}")
        # Cleanup on error
        for p in [id_path, live_path]:
            if p:
                try:
                    Path(p).unlink(missing_ok=True)
                except:
                    pass
        return None, False


def _ensure_jpeg(img_bytes: bytes) -> bytes:
    """Convert image bytes to JPEG if needed."""
    try:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        return img_bytes
