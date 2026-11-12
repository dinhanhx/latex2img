"""typer app: render, batch, amok, doctor."""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional

import typer
from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress
from typing_extensions import Annotated

from latex2img import amok as amoklib
from latex2img.config import Settings, load_settings
from latex2img.io import InputItem, ManifestWriter, read_inputs, read_single
from latex2img.pipeline import Sample, SampleBuilder, run_samples
from latex2img.randomize import sample_rng
from latex2img.renderers.base import BackendUnavailable, get_renderer
from latex2img.renderers.mathjax import check_assets

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Render LaTeX math to PNG/SVG.")

EXIT_FAILED, EXIT_USAGE, EXIT_BACKEND, EXIT_TIMEOUT = 1, 2, 3, 4

# --help panels
OUT, TEXT, WRAP, STYLE, RAND, LABEL, RUN = (
    "Output",
    "Text & fonts",
    "Wrapping",
    "Style",
    "Randomization",
    "Labels & manifest",
    "Run & debug",
)

Fmt = Annotated[
    Optional[str], typer.Option("-f", "--format", help="png | svg | pdf (pdf: future Tectonic)", rich_help_panel=OUT)
]
Backend = Annotated[
    Optional[str], typer.Option("--backend", help="mathjax (tectonic: future work)", rich_help_panel=OUT)
]
Lang = Annotated[
    Optional[str],
    typer.Option("--lang", help="Font stack / auto-text rules: en, vi, zh, ja, ko, ...", rich_help_panel=TEXT),
]
Font = Annotated[
    Optional[str], typer.Option("--font", help="Text font file or family; overrides lang map", rich_help_panel=TEXT)
]
Scale = Annotated[Optional[float], typer.Option("--scale", help="PNG device scale factor [2.0]", rich_help_panel=STYLE)]
Dpi = Annotated[Optional[int], typer.Option("--dpi", help="Reserved for future Tectonic backend", rich_help_panel=OUT)]
Display = Annotated[
    Optional[bool], typer.Option("--display/--inline", help="Display vs inline math", rich_help_panel=TEXT)
]
WrapText = Annotated[
    Optional[int],
    typer.Option("--wrap-text", help=r"Wrap \text{} longer than N chars [0=off]", rich_help_panel=WRAP),
]
WrapAlign = Annotated[Optional[str], typer.Option("--wrap-align", help="l | c | r", rich_help_panel=WRAP)]
WrapValign = Annotated[Optional[str], typer.Option("--wrap-valign", help="c | t | random", rich_help_panel=WRAP)]
WrapEq = Annotated[
    Optional[int], typer.Option("--wrap-eq", help="Break equation when width > N [0=off]", rich_help_panel=WRAP)
]
AutoText = Annotated[
    Optional[bool],
    typer.Option("--auto-text/--no-auto-text", help=r"Wrap bare non-ASCII words in \text{}", rich_help_panel=TEXT),
]
Color = Annotated[Optional[str], typer.Option("--color", help="Foreground [#000000]", rich_help_panel=STYLE)]
Bg = Annotated[Optional[str], typer.Option("--bg", help="Background [transparent]", rich_help_panel=STYLE)]
Padding = Annotated[
    Optional[int], typer.Option("--padding", help="Padding (px) after tight trim [4]", rich_help_panel=STYLE)
]
Timeout = Annotated[
    Optional[float], typer.Option("--timeout", help="Per-equation timeout, seconds [10]", rich_help_panel=RUN)
]
ConfigOpt = Annotated[Optional[Path], typer.Option("--config", help="TOML config path", rich_help_panel=RUN)]
KeepTemp = Annotated[
    Optional[bool],
    typer.Option("--keep-temp", help="Keep rendered .tex/raw output for debugging", rich_help_panel=RUN),
]
Verbose = Annotated[bool, typer.Option("-v", "--verbose", help="Debug logging to stderr", rich_help_panel=RUN)]


def _cli_overrides(values: dict[str, Any]) -> dict[str, Any]:
    """Only flags the user actually passed (non-None), so they win over JSONL/env/config."""
    return {k: v for k, v in values.items() if v is not None and v != []}


def _setup(config: Path | None, verbose: bool) -> Settings:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING, stream=sys.stderr, format="%(message)s")
    try:
        return load_settings(config)
    except (OSError, ValueError) as e:
        _usage(f"config: {e}")


def _usage(msg: str):
    typer.echo(f"error: {msg}", err=True)
    raise typer.Exit(EXIT_USAGE)


def _validate(s: Settings) -> None:
    if s.backend != "mathjax":
        _usage(f"backend {s.backend!r} is not available in v1 (only 'mathjax')")
    if s.format == "pdf":
        _usage("format pdf is reserved for the future Tectonic backend; use png or svg")
    if s.padding < 0:
        _usage("padding must be >= 0")
    checks = {
        "format": ("png", "svg"),
        "wrap_align": ("l", "c", "r"),
        "wrap_valign": ("c", "t", "random"),
        "color_mode": ("fixed", "random", "palette"),
        "label_source": ("rendered", "input"),
        "label_normalize": ("none", "canonical"),
    }
    for name, allowed in checks.items():
        if getattr(s, name) not in allowed:
            _usage(f"{name.replace('_', '-')} must be one of {', '.join(allowed)} (got {getattr(s, name)!r})")


async def _render_all(samples: list[Sample], s: Settings, **kw: Any):
    math_fonts = sorted({x.job.math_font for x in samples}) or ["mathjax-newcm"]
    renderer = get_renderer(
        s.backend,
        workers=s.workers,
        math_fonts=math_fonts,
        extensions=s.mathjax.get("extensions", []),
        macros=s.mathjax.get("macros", {}),
    )
    async with renderer:
        return await run_samples(samples, renderer, workers=s.workers, keep_temp=s.keep_temp, backend=s.backend, **kw)


def _build(builder: SampleBuilder, items: list[InputItem], base: Settings, cli: dict[str, Any], **kw: Any):
    samples: list[Sample] = []
    for item in items:
        try:
            s = base.merged(item.overrides).merged(cli)
            _validate(s)
            samples += builder.build(item, s, **kw)
        except (ValueError, OSError) as e:
            _usage(f"{item.source}: {e}")
    return samples


def _run(coro) -> Any:
    try:
        return asyncio.run(coro)
    except BackendUnavailable as e:
        typer.echo(f"error: backend unavailable: {e}", err=True)
        raise typer.Exit(EXIT_BACKEND)


@app.command()
def render(
    latex: Annotated[str, typer.Argument(help="Equation, or '-' for stdin")],
    output: Annotated[
        Optional[Path], typer.Option("-o", "--output", help="Output file [out.png]", rich_help_panel=OUT)
    ] = None,
    format: Fmt = None,  # noqa: A002
    backend: Backend = None,
    lang: Lang = None,
    font: Font = None,
    scale: Scale = None,
    dpi: Dpi = None,
    display: Display = None,
    wrap_text: WrapText = None,
    wrap_align: WrapAlign = None,
    wrap_valign: WrapValign = None,
    wrap_eq: WrapEq = None,
    auto_text: AutoText = None,
    color: Color = None,
    bg: Bg = None,
    padding: Padding = None,
    timeout: Timeout = None,
    config: ConfigOpt = None,
    keep_temp: KeepTemp = None,
    verbose: Verbose = False,
) -> None:
    """Render one equation to a file and print its path."""
    cli = _cli_overrides({k: v for k, v in locals().items() if k not in ("latex", "output", "config", "verbose")})
    base = _setup(config, verbose)
    eq = read_single(latex).strip()
    if not eq:
        _usage("empty equation")
    s = base.merged(cli)
    _validate(s)
    out = output or Path(f"out.{s.format}")
    samples = _build(SampleBuilder(out.parent), [InputItem("render", eq, "arg")], base, cli, image_path=out)
    stats = _run(_render_all(samples, s))
    if stats.timed_out:
        raise typer.Exit(EXIT_TIMEOUT)
    if stats.failed:
        raise typer.Exit(EXIT_FAILED)
    typer.echo(str(out))


@app.command()
def batch(
    input: Annotated[Path, typer.Argument(help=".txt (one per line) or .jsonl", exists=True, dir_okay=False)],  # noqa: A002
    output: Annotated[Path, typer.Option("-o", "--output", help="Output directory", rich_help_panel=OUT)] = Path("out"),
    format: Fmt = None,  # noqa: A002
    backend: Backend = None,
    lang: Lang = None,
    font: Font = None,
    scale: Scale = None,
    dpi: Dpi = None,
    display: Display = None,
    wrap_text: WrapText = None,
    wrap_align: WrapAlign = None,
    wrap_valign: WrapValign = None,
    wrap_eq: WrapEq = None,
    auto_text: AutoText = None,
    color: Color = None,
    bg: Bg = None,
    padding: Padding = None,
    variants: Annotated[
        Optional[int], typer.Option("--variants", help="Randomized renders per equation", rich_help_panel=RAND)
    ] = None,
    seed: Annotated[Optional[int], typer.Option("--seed", help="Base seed", rich_help_panel=RAND)] = None,
    font_pool: Annotated[
        Optional[List[str]], typer.Option("--font-pool", help="Text font files/dirs", rich_help_panel=RAND)
    ] = None,
    math_font_pool: Annotated[
        Optional[List[str]], typer.Option("--math-font-pool", help="MathJax fonts", rich_help_panel=RAND)
    ] = None,
    scale_range: Annotated[
        Optional[str], typer.Option("--scale-range", help="LO,HI log-uniform", rich_help_panel=RAND)
    ] = None,
    color_mode: Annotated[
        Optional[str], typer.Option("--color-mode", help="fixed | random | palette", rich_help_panel=RAND)
    ] = None,
    palette: Annotated[
        Optional[str], typer.Option("--palette", help="JSON list of {fg, bg}", rich_help_panel=RAND)
    ] = None,
    min_contrast: Annotated[
        Optional[float], typer.Option("--min-contrast", help="Min WCAG contrast", rich_help_panel=RAND)
    ] = None,
    white_bg_prob: Annotated[
        Optional[float], typer.Option("--white-bg-prob", help="P(white bg), random", rich_help_panel=RAND)
    ] = None,
    valign_t_prob: Annotated[
        Optional[float], typer.Option("--valign-t-prob", help="P(t), valign random", rich_help_panel=RAND)
    ] = None,
    wrap_text_range: Annotated[
        Optional[str], typer.Option("--wrap-text-range", help="LO,HI per sample", rich_help_panel=RAND)
    ] = None,
    wrap_eq_range: Annotated[
        Optional[str], typer.Option("--wrap-eq-range", help="LO,HI per sample", rich_help_panel=RAND)
    ] = None,
    padding_range: Annotated[
        Optional[str], typer.Option("--padding-range", help="LO,HI px per sample", rich_help_panel=RAND)
    ] = None,
    label_source: Annotated[
        Optional[str], typer.Option("--label-source", help="rendered | input", rich_help_panel=LABEL)
    ] = None,
    label_normalize: Annotated[
        Optional[str], typer.Option("--label-normalize", help="none | canonical", rich_help_panel=LABEL)
    ] = None,
    label_files: Annotated[
        Optional[bool], typer.Option("--label-files/--no-label-files", rich_help_panel=LABEL)
    ] = None,
    skip_existing: Annotated[Optional[bool], typer.Option("--skip-existing/--overwrite", rich_help_panel=OUT)] = None,
    manifest: Annotated[
        Optional[str], typer.Option("--manifest", help="Manifest path, '-' = stdout", rich_help_panel=LABEL)
    ] = None,
    timeout: Timeout = None,
    workers: Annotated[
        Optional[int], typer.Option("--workers", help="Concurrent Chromium pages [1]", rich_help_panel=RUN)
    ] = None,
    continue_on_error: Annotated[
        Optional[bool],
        typer.Option("--continue-on-error/--fail-fast", help="Batch error policy", rich_help_panel=RUN),
    ] = None,
    config: ConfigOpt = None,
    keep_temp: KeepTemp = None,
    verbose: Verbose = False,
) -> None:
    """Render a .txt/.jsonl file of equations into OUTPUT/images + manifest.jsonl."""
    cli = _cli_overrides({k: v for k, v in locals().items() if k not in ("input", "output", "config", "verbose")})
    base = _setup(config, verbose)
    try:
        items = read_inputs(input)
    except (ValueError, OSError) as e:
        _usage(str(e))
    s = base.merged(cli)
    _validate(s)
    samples = _build(SampleBuilder(output), items, base, cli)
    seen: set[str] = set()
    for x in samples:
        if x.id in seen:
            _usage(f"duplicate output id {x.id!r} ({x.source})")
        seen.add(x.id)
    writer = ManifestWriter(s.manifest or output / "manifest.jsonl")
    # stderr only, and off when not a terminal (pipes, CI); stdout may carry the manifest (--manifest -)
    bar = Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=Console(stderr=True),
                   disable=not sys.stderr.isatty(), redirect_stdout=False)  # fmt: skip
    task = bar.add_task("Rendering", total=len(samples))
    handlers = [h for h in logging.getLogger().handlers if isinstance(h, logging.StreamHandler)]
    streams = [h.stream for h in handlers]
    try:
        with bar:
            for h in handlers:  # route log lines through rich's stderr proxy so they print above the bar
                h.setStream(sys.stderr)
            stats = _run(
                _render_all(
                    samples,
                    s,
                    manifest=writer,
                    skip_existing=s.skip_existing,
                    fail_fast=not s.continue_on_error,
                    label_files=s.label_files,
                    on_done=lambda: bar.advance(task),
                )
            )
    finally:
        for h, stream in zip(handlers, streams):
            h.setStream(stream)
        writer.close()
    logging.getLogger(__name__).info("ok=%d failed=%d skipped=%d", stats.ok, stats.failed, stats.skipped)
    if stats.failed:
        raise typer.Exit(EXIT_FAILED)


@app.command()
def amok(
    count: Annotated[int, typer.Argument(help="Number of formulas")],
    output: Annotated[Optional[Path], typer.Option("-o", "--output", help="Output .txt [stdout]")] = None,
    seed: Annotated[int, typer.Option("--seed", help="Base seed")] = 0,
    lang: Annotated[str, typer.Option("--lang", help=r"\text{} word list: en, vi, zh")] = "en",
    depth: Annotated[int, typer.Option("--depth", help="Max nesting depth (grammar)")] = 3,
    source: Annotated[
        Optional[Path], typer.Option("--from", exists=True, dir_okay=False, help="Mutate this .txt/.jsonl corpus")
    ] = None,
) -> None:
    """Print random LaTeX formulas, one per line (feed the file to `batch`)."""
    if count < 1 or depth < 0:
        _usage("count must be >= 1 and depth >= 0")
    items = []
    if source:
        try:
            items = read_inputs(source)
        except (ValueError, OSError) as e:
            _usage(str(e))
        if not items:
            _usage(f"{source}: no formulas")
    lines = []
    for k in range(count):
        rng = sample_rng(seed, "amok", k)
        eq = amoklib.mutate(rng, items[k % len(items)].latex, lang) if items else amoklib.generate(rng, lang, depth)
        lines.append(" ".join(eq.split()))  # one formula per line
    text = "\n".join(lines) + "\n"
    if output:
        output.write_text(text, encoding="utf-8")
    else:
        typer.echo(text, nl=False)


@app.command()
def doctor(config: ConfigOpt = None, verbose: Verbose = False) -> None:
    """Check that Chromium and the vendored MathJax assets are available."""
    s = _setup(config, verbose)
    fonts = sorted({f if f.startswith("mathjax-") else f"mathjax-{f}" for f in s.mathjax.get("math_fonts", [])})
    missing = check_assets(fonts or ["mathjax-newcm"], s.mathjax.get("extensions", []))
    for m in missing:
        typer.echo(f"FAIL {m}", err=True)
    if missing:
        raise typer.Exit(EXIT_BACKEND)
    typer.echo("ok   MathJax assets", err=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "doctor.png"
        samples = SampleBuilder(Path(tmp)).build(InputItem("doctor", r"E = mc^2", "doctor"), s, image_path=out)
        stats = _run(_render_all(samples, s))
        if stats.failed or not out.exists():
            typer.echo("FAIL test render", err=True)
            raise typer.Exit(EXIT_BACKEND)
    typer.echo("ok   Chromium + test render", err=True)
