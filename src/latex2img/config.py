"""Settings + TOML loading. Precedence: CLI > JSONL item > env (LATEX2IMG_*) > --config > ./latex2img.toml
> [tool.latex2img] in pyproject.toml > defaults."""

from __future__ import annotations

import dataclasses
import os
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Settings:
    format: str = "png"
    backend: str = "mathjax"
    lang: str = "vi"
    font: str | None = None
    scale: float = 2.0
    dpi: int = 300  # reserved for the future Tectonic backend
    display: bool = True
    wrap_text: int = 0
    wrap_align: str = "c"
    wrap_valign: str = "c"
    wrap_eq: int = 0
    auto_text: bool = True
    color: str = "#000000"
    bg: str = "transparent"
    padding: int = 4
    workers: int = 1
    timeout: float = 10.0
    continue_on_error: bool = True
    keep_temp: bool = False
    verbose: bool = False
    # batch / training data
    variants: int = 1
    seed: int = 0
    font_pool: list[str] = field(default_factory=list)
    math_font_pool: list[str] = field(default_factory=list)
    scale_range: str | None = None  # "LO,HI"
    color_mode: str = "fixed"
    palette: str | None = None
    min_contrast: float = 4.5
    white_bg_prob: float = 0.5
    valign_t_prob: float = 0.5
    wrap_text_range: str | None = None
    wrap_eq_range: str | None = None
    padding_range: str | None = None  # "LO,HI" px, per sample; overrides padding
    label_source: str = "rendered"
    label_normalize: str = "none"
    label_files: bool = False
    skip_existing: bool = True
    manifest: str | None = None
    # tables
    fonts: dict[str, str] = field(default_factory=dict)
    mathjax: dict[str, Any] = field(default_factory=dict)
    label: dict[str, Any] = field(default_factory=dict)

    def merged(self, overrides: dict[str, Any]) -> Settings:
        """Copy with overrides applied; unknown keys raise ValueError."""
        known = {f.name for f in fields(self)}
        bad = set(overrides) - known
        if bad:
            raise ValueError(f"unknown setting(s): {', '.join(sorted(bad))}")
        return dataclasses.replace(self, **overrides)


_TYPES = {f.name: f.type for f in fields(Settings)}


def _coerce(name: str, raw: str) -> Any:
    typ = str(_TYPES[name])
    if typ.startswith("bool"):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if typ.startswith("int"):
        return int(raw)
    if typ.startswith("float"):
        return float(raw)
    if typ.startswith("list"):
        return [s for s in raw.split(os.pathsep) if s]
    return raw


def _toml_settings(data: dict[str, Any]) -> dict[str, Any]:
    return {k.replace("-", "_"): v for k, v in data.items()}


def load_settings(config_path: Path | None = None, cwd: Path | None = None) -> Settings:
    """Settings from defaults < pyproject < ./latex2img.toml < --config < env. CLI/JSONL are merged by callers."""
    cwd = cwd or Path.cwd()
    layers: list[dict[str, Any]] = []
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        layers.append(tomllib.loads(pyproject.read_text()).get("tool", {}).get("latex2img", {}))
    if (cwd / "latex2img.toml").exists():
        layers.append(tomllib.loads((cwd / "latex2img.toml").read_text()))
    if config_path is not None:
        layers.append(tomllib.loads(Path(config_path).read_text()))
    settings = Settings()
    for layer in layers:
        settings = settings.merged(_toml_settings(layer))
    env = {
        k[len("LATEX2IMG_") :].lower(): v
        for k, v in os.environ.items()
        if k.startswith("LATEX2IMG_") and k[len("LATEX2IMG_") :].lower() in _TYPES
    }
    return settings.merged({k: _coerce(k, v) for k, v in env.items() if k not in ("fonts", "mathjax", "label")})
