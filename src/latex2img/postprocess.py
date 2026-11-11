"""PNG post-processing: tight trim, padding, background composite."""

from __future__ import annotations

import io

from PIL import Image, ImageColor


def finish_png(png: bytes, background: str | None, padding: int) -> tuple[bytes, int, int]:
    """Trim to non-transparent bbox, pad, composite onto background (None keeps alpha)."""
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    padded = Image.new("RGBA", (img.width + 2 * padding, img.height + 2 * padding), (0, 0, 0, 0))
    padded.paste(img, (padding, padding))
    if background is not None:
        canvas = Image.new("RGBA", padded.size, ImageColor.getrgb(background))
        padded = Image.alpha_composite(canvas, padded).convert("RGB")
    buf = io.BytesIO()
    padded.save(buf, format="PNG")
    return buf.getvalue(), padded.width, padded.height
