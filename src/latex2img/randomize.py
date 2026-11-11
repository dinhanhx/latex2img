"""Per-sample RNG and font/scale/color/layout sampling for synthetic training data."""

from __future__ import annotations

import colorsys
import hashlib
import json
import math
import random
from pathlib import Path

from PIL import ImageColor

SCALE_BUCKETS = 8  # one browser context per bucket; sampled scales snap to the nearest


def sample_rng(seed: int, source_id: str, k: int) -> random.Random:
    """RNG for one sample, independent of worker order: hash(seed, id, k)."""
    digest = hashlib.sha256(f"{seed}\x00{source_id}\x00{k}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def sample_scale(rng: random.Random, lo: float, hi: float) -> float:
    """Log-uniform in [lo, hi], snapped to one of SCALE_BUCKETS log-spaced values."""
    if hi <= lo:
        return lo
    x = rng.uniform(math.log(lo), math.log(hi))
    step = (math.log(hi) - math.log(lo)) / (SCALE_BUCKETS - 1)
    return round(math.exp(math.log(lo) + round((x - math.log(lo)) / step) * step), 4)


def sample_int(rng: random.Random, lo: int, hi: int) -> int:
    return rng.randint(lo, hi)


def _luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(fg: str, bg: str) -> float:
    """WCAG 2 contrast ratio between two #rrggbb colors."""
    a, b = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _hsl(rng: random.Random) -> str:
    r, g, b = colorsys.hls_to_rgb(rng.random(), rng.random(), rng.random())
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def sample_colors(rng: random.Random, min_contrast: float, white_bg_prob: float) -> tuple[str, str]:
    for _ in range(1000):
        bg = "#ffffff" if rng.random() < white_bg_prob else _hsl(rng)
        fg = _hsl(rng)
        if contrast(fg, bg) >= min_contrast:
            return fg, bg
    return "#000000", "#ffffff"


def load_palette(path: str | Path) -> list[dict[str, str]]:
    pairs = json.loads(Path(path).read_text())
    if not pairs or not all("fg" in p and "bg" in p for p in pairs):
        raise ValueError(f"palette {path}: expected a non-empty JSON list of {{fg, bg}}")
    return [{k: to_hex(p[k]) for k in ("fg", "bg")} for p in pairs]


def to_hex(color: str) -> str:
    return "#{:02x}{:02x}{:02x}".format(*ImageColor.getrgb(color)[:3])


def sample_palette(rng: random.Random, pairs: list[dict[str, str]], min_contrast: float) -> tuple[str, str]:
    ok = [p for p in pairs if contrast(p["fg"], p["bg"]) >= min_contrast] or pairs
    pick = rng.choice(ok)
    return pick["fg"], pick["bg"]
