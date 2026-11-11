from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path


class OutputFormat(str, enum.Enum):
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"


@dataclass(frozen=True)
class RenderJob:
    id: str
    latex: str  # after preprocessing
    fmt: OutputFormat = OutputFormat.PNG
    lang: str = "vi"
    font: Path | None = None  # text font file for \text{} content
    math_font: str = "mathjax-newcm"
    display: bool = True
    scale: float = 2.0
    color: str = "#000000"
    background: str | None = None  # None = transparent
    padding_px: int = 4
    timeout_s: float = 10.0


@dataclass
class RenderResult:
    job_id: str
    data: bytes | None
    fmt: OutputFormat
    width_px: int | None = None
    height_px: int | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None
