"""Generate PWA icons for WFP Verify app."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "logo-kit" / "logo-dark-bg-512.png"
OUTPUT_DIR = BASE_DIR / "frontend" / "verify" / "public"
NAVY = (0x1B, 0x2A, 0x4A)


def find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font, fall back to default."""
    candidates = [
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "arial.ttf",
        "Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    # Last resort: PIL default (bitmap, ignores size)
    return ImageFont.load_default()


def make_icon(size: int, logo_size: int, font_size: int, output_path: Path) -> None:
    canvas = Image.new("RGBA", (size, size), NAVY + (255,))
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Paste logo centered, shifted up to leave room for text
    text_reserve = int(size * 0.12)
    logo_x = (size - logo_size) // 2
    logo_y = (size - logo_size - text_reserve) // 2
    canvas.paste(logo, (logo_x, logo_y), logo)  # use alpha mask

    # Draw text
    draw = ImageDraw.Draw(canvas)
    font = find_font(font_size)
    text = "WFP Verify"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_x = (size - tw) // 2
    text_y = logo_y + logo_size + (text_reserve - th) // 2
    draw.text((text_x, text_y), text, fill="white", font=font)

    # Save as RGB PNG (no transparency needed for final icon)
    canvas.convert("RGB").save(output_path, "PNG")
    print(f"Saved {output_path} ({size}x{size})")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    make_icon(512, 300, 36, OUTPUT_DIR / "icon-512.png")
    make_icon(192, 120, 14, OUTPUT_DIR / "icon-192.png")


if __name__ == "__main__":
    main()
