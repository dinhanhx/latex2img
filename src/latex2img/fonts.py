"""Language -> text font resolution and cmap coverage checks."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

ASSETS = Path(__file__).parent / "assets"
_NOTO_SERIF = str(ASSETS / "fonts" / "NotoSerif-Regular.ttf")
_CJK = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
# value: font file, optionally "file.ttc#Family Name" to pick a face from a collection
DEFAULT_FONTS = {
    "en": _NOTO_SERIF,
    "vi": _NOTO_SERIF,
    "zh": f"{_CJK}#Noto Serif CJK SC",
    "ja": f"{_CJK}#Noto Serif CJK JP",
    "ko": f"{_CJK}#Noto Serif CJK KR",
}
CACHE = Path.home() / ".cache" / "latex2img" / "fonts"
FONT_SUFFIXES = (".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2")


def font_for_lang(lang: str, overrides: dict[str, str] | None = None) -> str:
    # "other" languages get Noto Serif; missing glyphs fall back to the page's CSS serif
    return {**DEFAULT_FONTS, **(overrides or {})}.get(lang, _NOTO_SERIF)


def resolve_font(spec: str, base: Path | None = None) -> Path:
    """Font spec (path, 'collection.ttc#Family', or family name) -> a single-face font file."""
    path_str, _, family = spec.partition("#")
    path = Path(path_str).expanduser()
    if not path.is_absolute() and base is not None and (base / path).exists():
        path = base / path
    if not path.exists() and not path.is_absolute() and (ASSETS.parent / path).exists():
        path = ASSETS.parent / path  # config paths like "assets/fonts/..." are package-relative
    if not path.exists():
        if path.suffix.lower() in FONT_SUFFIXES or "/" in path_str:
            raise FileNotFoundError(f"font file not found: {path_str}")
        path = _fc_match(path_str)
    if path.suffix.lower() in (".ttc", ".otc"):
        return _extract_face(path, family)
    return path


def _fc_match(family: str) -> Path:
    # shortcut: family names resolve through fontconfig (machine-dependent); pass a file path for determinism
    if not shutil.which("fc-match"):
        raise FileNotFoundError(f"font {family!r}: not a file and fc-match is unavailable")
    out = subprocess.run(["fc-match", "-f", "%{file}", family], capture_output=True, text=True, check=True).stdout
    return Path(out)


def _extract_face(path: Path, family: str) -> Path:
    """Chromium @font-face cannot pick a face from a .ttc, so save the wanted face as its own file (cached)."""
    key = hashlib.sha1(f"{path.resolve()}#{family}#{path.stat().st_mtime_ns}".encode()).hexdigest()[:16]
    out = CACHE / f"{path.stem}-{family.replace(' ', '')}-{key[:8]}.otf"
    if out.exists():
        return out
    coll = TTCollection(str(path))
    faces = [f for f in coll.fonts if not family or f["name"].getDebugName(1) == family]
    if not faces:
        raise FileNotFoundError(f"no face {family!r} in {path}")
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    faces[0].save(str(tmp))
    tmp.replace(out)
    return out


def expand_pool(entries: list[str]) -> list[Path]:
    """--font-pool entries (files or directories) -> sorted font files."""
    files: list[Path] = []
    for entry in entries:
        p = Path(entry).expanduser()
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*") if f.suffix.lower() in (".ttf", ".otf")))
        elif p.exists():
            files.append(p)
        else:
            raise FileNotFoundError(f"--font-pool entry not found: {entry}")
    return files


@lru_cache(maxsize=256)
def _cmap(path: Path) -> frozenset[int]:
    with TTFont(str(path), lazy=True) as font:
        return frozenset(font.getBestCmap() or {})


def covers(path: Path, chars: str) -> bool:
    cmap = _cmap(path)
    return all(ord(c) in cmap for c in set(chars) if not c.isspace())
