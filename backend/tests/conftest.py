"""Test fixtures for integration tests.

Tests run against the live Docker services via HTTP — this avoids
asyncpg event loop conflicts with pytest-asyncio's loop management.
The full E2E curl flow has already proven all contracts work.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, Timeout

# Base URL of the running API service
API_BASE = "http://localhost:8000"

# Registration involves DeepFace inference — allow up to 60s
TIMEOUT = Timeout(60.0, connect=10.0)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as ac:
        yield ac


@pytest.fixture
def test_images():
    """Create minimal test images in memory."""
    from PIL import Image, ImageDraw
    import io

    def make_img(w, h, color):
        img = Image.new('RGB', (w, h), color)
        draw = ImageDraw.Draw(img)
        cx, cy = w // 2, h // 2
        r = min(w, h) // 3
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill='#FFD5B4')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    return {
        'id_document': make_img(800, 600, '#224488'),
        'id_face_crop': make_img(300, 400, '#334455'),
        'face_photo': make_img(400, 400, '#445566'),
    }
