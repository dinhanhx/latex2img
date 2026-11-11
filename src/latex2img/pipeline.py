"""Load -> normalize -> wrap -> render -> post-process -> write, shared by `render` and `batch`."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from latex2img import fonts as fontlib
from latex2img.config import Settings
from latex2img.io import InputItem, ManifestWriter
from latex2img.labels import canonicalize
from latex2img.models import OutputFormat, RenderJob, RenderResult
from latex2img.postprocess import finish_png
from latex2img.preprocess import expand_ml, normalize, wrap_equation, wrap_text
from latex2img.preprocess.tokenizer import TEXT_COMMANDS, command_arg, tokenize
from latex2img.randomize import load_palette, sample_colors, sample_int, sample_palette, sample_rng, sample_scale
from latex2img.renderers.base import Renderer

log = logging.getLogger(__name__)
DEFAULT_MATH_FONT = "mathjax-newcm"


@dataclass
class Sample:
    id: str
    source_id: str
    variant: int
    source: str
    latex_in: str
    latex_rendered: str
    label: str
    label_raw: str | None
    params: dict[str, Any]
    job: RenderJob
    image_path: Path
    image_rel: str
    padding: int
    warnings: list[str] = field(default_factory=list)


def parse_range(value: str | None, cast=float) -> tuple[Any, Any] | None:
    if not value:
        return None
    lo, hi = (cast(v) for v in value.split(","))
    if lo > hi:
        raise ValueError(f"range {value!r}: LO > HI")
    return lo, hi


def math_font_name(name: str) -> str:
    return name if name.startswith("mathjax-") else f"mathjax-{name}"


def text_chars(latex: str) -> str:
    tokens = tokenize(latex)
    chars = []
    for i, tok in enumerate(tokens):
        if tok in TEXT_COMMANDS and (arg := command_arg(tokens, i)):
            chars.append("".join(tokens[arg[0] + 1 : arg[1]]))
    return "".join(chars).replace("\\\\", "")


def _source_id(latex: str, s: Settings) -> str:
    opts = {k: v for k, v in asdict(s).items() if k not in ("workers", "verbose", "manifest", "keep_temp")}
    return hashlib.sha1((latex + json.dumps(opts, sort_keys=True, default=str)).encode()).hexdigest()[:12]


class SampleBuilder:
    """Turns input items into per-variant samples (all randomization happens here, before rendering)."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self._palettes: dict[str, list[dict[str, str]]] = {}
        self._pools: dict[tuple[str, ...], list[Path]] = {}

    def build(self, item: InputItem, s: Settings, image_path: Path | None = None) -> list[Sample]:
        fmt = OutputFormat(s.format)
        source_id = item.id or _source_id(item.latex, s)
        try:
            normalized = normalize(item.latex, s.auto_text)
            chars = text_chars(expand_ml(normalized))
            pre_error = None
        except ValueError as e:  # malformed input (e.g. unbalanced braces): let the renderer report it
            normalized, chars, pre_error = normalize(item.latex, False), "", f"preprocessing skipped: {e}"
        scale_range = parse_range(s.scale_range)
        wt_range = parse_range(s.wrap_text_range, int)
        we_range = parse_range(s.wrap_eq_range, int)
        pad_range = parse_range(s.padding_range, int)
        if pad_range and pad_range[0] < 0:
            raise ValueError("--padding-range must be >= 0")
        math_pool = [
            math_font_name(f) for f in (s.math_font_pool or s.mathjax.get("math_fonts") or [DEFAULT_MATH_FONT])
        ]
        text_pool = self._pool(s.font_pool)
        training = s.variants > 1 or s.color_mode != "fixed"

        samples = []
        for k in range(s.variants):
            rng = sample_rng(s.seed, source_id, k)
            sample_seed = rng.getrandbits(32)
            warnings: list[str] = [pre_error] if pre_error else []

            lang_font = fontlib.resolve_font(s.font or fontlib.font_for_lang(s.lang, s.fonts))
            text_font = lang_font
            if text_pool:
                covering = [f for f in text_pool if fontlib.covers(f, chars)]
                if covering:
                    text_font = rng.choice(covering)
                else:
                    warnings.append("no --font-pool font covers the text characters; using the lang-map font")
            if chars and not fontlib.covers(text_font, chars):
                warnings.append(f"text font {text_font.name} lacks glyphs for some text characters")
            math_font = rng.choice(math_pool)
            scale = sample_scale(rng, *scale_range) if scale_range else s.scale

            if s.color_mode == "random":
                fg, bg = sample_colors(rng, s.min_contrast, s.white_bg_prob)
            elif s.color_mode == "palette":
                if not s.palette:
                    raise ValueError("--color-mode palette needs --palette FILE")
                fg, bg = sample_palette(rng, self._palette(s.palette), s.min_contrast)
            else:
                fg, bg = s.color, (None if s.bg in ("transparent", "none", "") else s.bg)
            if training and bg is None:
                bg = "#ffffff"  # training images are always composited: the VLM never sees alpha

            valign = s.wrap_valign
            if valign == "random":
                valign = "t" if rng.random() < s.valign_t_prob else "c"
            wt = sample_int(rng, *wt_range) if wt_range else s.wrap_text
            we = sample_int(rng, *we_range) if we_range else s.wrap_eq
            padding = sample_int(rng, *pad_range) if pad_range else s.padding

            rendered = normalized
            if not pre_error:
                try:
                    # \text wrapping first: \ml lines are manual breaks and must not be re-wrapped by width
                    rendered = wrap_text(normalized, wt, s.wrap_align, valign)
                    rendered = expand_ml(rendered, s.wrap_align, valign)
                    rendered, eq_warnings = wrap_equation(rendered, we)
                    warnings += eq_warnings
                except ValueError as e:
                    rendered = normalized
                    warnings.append(f"wrapping skipped: {e}")

            label_raw = rendered if s.label_source == "rendered" else item.latex
            label, raw = label_raw, None
            if s.label_normalize == "canonical":
                try:
                    label, raw = canonicalize(label_raw, s.label.get("synonyms")), label_raw
                except ValueError as e:
                    warnings.append(f"label not canonicalized: {e}")

            sid = source_id if s.variants == 1 else f"{source_id}_{k:02d}"
            rel = f"images/{sid}.{fmt.value}"
            params = {
                "text_font": text_font.name,
                "math_font": math_font,
                "scale": scale,
                "fg": fg,
                "bg": bg,
                "wrap_text": wt,
                "wrap_eq": we,
                "padding": padding,
                "wrap_valign": valign,
                "seed": sample_seed,
            }
            job = RenderJob(
                id=sid,
                latex=rendered,
                fmt=fmt,
                lang=s.lang,
                font=text_font,
                math_font=math_font,
                display=s.display,
                scale=scale,
                color=fg,
                background=bg,
                padding_px=padding,
                timeout_s=s.timeout,
            )
            samples.append(
                Sample(
                    sid, source_id, k, item.source, item.latex, rendered, label, raw, params, job,
                    image_path or self.out_dir / rel, rel, padding, warnings,
                )
            )  # fmt: skip
        return samples

    def _pool(self, entries: list[str]) -> list[Path]:
        key = tuple(entries)
        if key not in self._pools:
            self._pools[key] = fontlib.expand_pool(entries)
        return self._pools[key]

    def _palette(self, path: str) -> list[dict[str, str]]:
        if path not in self._palettes:
            self._palettes[path] = load_palette(path)
        return self._palettes[path]


@dataclass
class RunStats:
    ok: int = 0
    failed: int = 0
    skipped: int = 0
    timed_out: int = 0


async def run_samples(
    samples: list[Sample],
    renderer: Renderer,
    *,
    workers: int,
    manifest: ManifestWriter | None = None,
    skip_existing: bool = False,
    fail_fast: bool = False,
    label_files: bool = False,
    keep_temp: bool = False,
    backend: str = "mathjax",
    on_done: Callable[[], None] | None = None,
) -> RunStats:
    stats = RunStats()
    it = iter(samples)
    stop = asyncio.Event()
    temp_dir = Path(tempfile.mkdtemp(prefix="latex2img-")) if keep_temp else None
    if temp_dir:
        print(f"keeping temp files in {temp_dir}", file=sys.stderr)

    async def one(sample: Sample) -> None:
        if temp_dir:
            (temp_dir / f"{sample.id}.tex").write_text(sample.latex_rendered + "\n", encoding="utf-8")
        if skip_existing and sample.image_path.exists():
            result = RenderResult(sample.id, None, sample.job.fmt)
            if sample.job.fmt is OutputFormat.PNG:
                with Image.open(sample.image_path) as im:
                    result.width_px, result.height_px = im.size
            stats.skipped += 1
        else:
            result = await renderer.render(sample.job)
            if result.ok and result.data is not None:
                data = result.data
                if sample.job.fmt is OutputFormat.PNG:
                    data, result.width_px, result.height_px = finish_png(data, sample.job.background, sample.padding)
                sample.image_path.parent.mkdir(parents=True, exist_ok=True)
                sample.image_path.write_bytes(data)
                if temp_dir:
                    (temp_dir / sample.image_path.name).write_bytes(result.data)
                stats.ok += 1
            else:
                stats.failed += 1
                stats.timed_out += result.timed_out
                print(f"error [{sample.id}] ({sample.source}): {result.error}", file=sys.stderr)
                if fail_fast:
                    stop.set()
        for w in sample.warnings + result.warnings:
            log.warning("[%s] %s", sample.id, w)
        if label_files and result.ok and sample.image_path.parent.name == "images":
            labels = sample.image_path.parent.parent / "labels"
            labels.mkdir(parents=True, exist_ok=True)
            (labels / f"{sample.id}.tex").write_text(sample.label + "\n", encoding="utf-8")
        if manifest is not None:
            manifest.write(_row(sample, result, backend))
        if on_done:
            on_done()

    async def worker() -> None:
        for sample in it:
            if stop.is_set():
                return
            await one(sample)

    await asyncio.gather(*(worker() for _ in range(max(1, workers))))
    return stats


def _row(sample: Sample, result: RenderResult, backend: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": sample.id,
        "source_id": sample.source_id,
        "variant": sample.variant,
        "source": sample.source,
        "image": sample.image_rel if result.ok else None,
        "label": sample.label,
    }
    if sample.label_raw is not None:
        row["label_raw"] = sample.label_raw
    row.update(
        latex_in=sample.latex_in,
        latex_rendered=sample.latex_rendered,
        backend=backend,
        width=result.width_px,
        height=result.height_px,
        params=sample.params,
        error=result.error,
        warnings=sample.warnings + result.warnings,
    )
    return row
