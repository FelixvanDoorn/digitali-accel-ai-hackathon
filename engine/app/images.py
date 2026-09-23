"""Image preprocessing. Everything happens in memory; nothing is written to disk."""

import base64
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF"}


class InvalidImage(ValueError):
    pass


@dataclass
class PreparedImage:
    jpeg: bytes
    width: int
    height: int
    source_format: str

    def data_url(self) -> str:
        return "data:image/jpeg;base64," + base64.b64encode(self.jpeg).decode()


def prepare(raw: bytes, max_edge: int) -> PreparedImage:
    """Fix rotation, drop metadata (incl. GPS), downscale and re-encode as JPEG."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise InvalidImage("File is not a readable image") from e

    source_format = img.format or "UNKNOWN"
    if source_format not in ALLOWED_FORMATS:
        raise InvalidImage(f"Unsupported image format: {source_format}")

    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_edge, max_edge))

    # Saving without exif= writes a clean JPEG with no metadata.
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return PreparedImage(out.getvalue(), img.width, img.height, source_format)
