# latex2img — CLI Spec

Nov 11, 2026 · @Anh Vu Dinh

## Overview

`latex2img` renders LaTeX math to PNG (SVG for debugging) from the command line, with Unicode text (Vietnamese and other scripts) inside equations and automatic multi-line wrapping of long textual variable names. v1 has one backend: MathJax 4.1 in headless Chromium, the default and only choice. Tectonic is future work; the `Renderer` protocol keeps room for it.

Labels used below: **\[Unverified\]** = not checked against current docs/releases, confirm before implementing; **\[Inference\]** = engineering judgement, not measured; **\[Verified\]** = checked against the v0.1.0 implementation (MathJax 4.1.3, Playwright 1.65, pixi 0.84.2, uv 0.13.6, ruff 0.17.4) on linux-64.

**Status:** v0.1.0 implemented. Where the implementation differs from the original plan, the text below describes what was built; see "Implementation notes" at the end for the list of deviations.

**Goals**

- Single equation (arg/stdin) and batch (txt one-per-line / JSONL) rendering, with per-sample font/scale/color randomization for synthetic training data.
- Random formula generation (`amok`) to produce batch input without a hand-written corpus.
- Correct rendering of Vietnamese diacritics in `\text{}` and bare Unicode in math, with a per-language font map for other scripts.
- Auto-wrap long `\text{...}` names (e.g. `\text{price of agricultural land}`) onto multiple stacked lines; optional wrap of whole equations at top-level relations/operators.
- Deterministic output (pinned fonts, pinned renderer assets), runnable fully offline.
- Python ≥ 3.10 (pixi dev env pinned to 3.10, the floor), `uv` (via pixi, conda-forge only), ruff config as given.

**Non-goals (v1)**

- LaTeX → MathML/accessibility output.
- Tectonic (full LaTeX) backend; see Future work.
- Full-document (non-math) rendering.
- Non-x86\_64 hosts (arm64, Jetson). GUI / HTTP server (the renderer API should make a FastAPI wrapper trivial later).

## Backend: MathJax (Playwright); Tectonic deferred

**Decision:** MathJax 4.1 via Playwright is the default and only backend in v1. Tectonic moves to Future work. The comparison below is kept as the rationale and as input for that work.

| Criterion | MathJax via Playwright/Chromium | Tectonic via CLI |
| --- | --- | --- |
| LaTeX coverage | Math-mode subset: amsmath envs (`aligned`, `multline`, `array`, `matrix`), extensions like `mhchem`. No arbitrary packages, no `\parbox` | Full XeTeX: any package (`breqn`, `mathtools`, `fontspec`, `xeCJK`) |
| Unicode / Vietnamese in `\text{}` | Works. \[Verified\] By default MathJax 4.1 draws `\text{}` with its own math-font glyphs where it has them and falls back to `<text font-family=serif>` otherwise. To force the language font, set `output.mtextInheritFont: true` **and** pass `family` to `tex2svgPromise`; the font itself is loaded with the `FontFace` API from a vendored file | Works with `fontspec` + a font with Vietnamese coverage (e.g. Noto Serif). Glyphs come from a pinned font file |
| Native output | SVG (from MathJax), PNG (element screenshot) | PDF only → needs `pdftocairo` (SVG/PNG) or `pypdfium2` (PNG) |
| SVG portability | `\text{}` content is emitted as SVG `<text>` (when `family` is passed), so it depends on fonts on the viewer's machine \[Verified\] | `pdftocairo -svg` outlines glyphs to paths → self-contained SVG |
| Latency per equation | Low once the browser and page are warm; one page reused for many equations \[Inference: ms range\] | One XeTeX run per document; amortize by putting N equations into one `standalone` multi-page doc \[Inference: 100s of ms to seconds per run\] |
| Process model | Long-lived Chromium; async API, easy concurrency via multiple pages | Stateless subprocess; concurrency via a process pool |
| Offline / airgapped | Vendor MathJax JS into the package; ship Chromium via `PLAYWRIGHT_BROWSERS_PATH` | Pre-warm Tectonic's package cache (or a local bundle) on a connected host, copy it, run with `--only-cached` \[Unverified: flag name for your Tectonic version\] |
| Footprint | Chromium headless shell + system libs (`playwright install-deps`); the headless shell download is 126 MiB \[Verified, Playwright 1.65\] | Single binary + package cache + poppler-utils |
| Error reporting | MathJax returns `merror` nodes; parse from DOM. The `noundefined` TeX package is removed so unknown macros raise an error instead of rendering as red text \[Verified\] | TeX log; parse ` !  ` lines + line numbers |
| Automatic line breaking | MathJax 4.1: automatic breaking for display and inline math, including long \\text{} content (\[v4 release notes\](https://github.com/mathjax/mathjax-v3/releases/tag/4.0.0-alpha.1)) | `breqn` (fragile) |
| Jetson / arm64 | Out of scope: x86\_64 only | Out of scope: x86\_64 only |

Line breaking is not delegated to MathJax. The preprocessor rewrites LaTeX into plain constructs (`matrix`, `array`, `aligned`) that any TeX-compatible renderer handles, so labels stay valid if Tectonic is added later.

**MathJax pinned to 4.1.3** ([docs](https://docs.mathjax.org/en/v4.1/output/fonts.html)). Vendored: the 4.1.3 component files (v4 drops the `/es5` directory), `@mathjax/mathjax-{newcm,stix2,pagella}-font@4.1.3`, and `@mathjax/mathjax-mhchem-font-extension@4.1.3`. Font packages are pruned to `svg.js` + `svg/` (the browser never loads `cjs/`, `mjs/`, `chtml/`), so assets are ≈37 MB. v4's own line breaking stays off (`linebreaks: {inline: false, width: "100000em"}`): the preprocessor does the wrapping so both backends produce the same layout and the label matches the image.

\[Verified\] Offline loading needs three loader settings, not just `output.fontPath`: `loader.paths[<font>]` for the math font, `loader.paths.fonts` for font *extensions* (mhchem's otherwise comes from `cdn.jsdelivr.net`, and autoloading `\ce` triggers it), and a `loader.failed` hook so a missing file fails fast instead of hanging. The renderer serves assets from a fake origin (`http://latex2img.local/`) through `page.route` and aborts every other request, so a missing vendored file can never fall back to a CDN.

Alternative worth noting: MathJax can run in Node directly (`mathjax-full` with the lite DOM adaptor), no browser. That removes Chromium but adds Node and gives SVG only (PNG needs a rasterizer like `resvg`). Out of scope unless Chromium footprint is a problem.

## CLI interface

Three subcommands (`render`, `batch`, `amok`) plus `doctor` for backend checks. Built with `typer`.

```bash
# single equation -> file
latex2img render 'P = \text{giá đất nông nghiệp} \times S' -o out.png

# stdin, SVG for debugging
echo 'E = mc^2' | latex2img render - -f svg -o e.svg

# batch from JSONL, 4 workers, wrap text names at 16 chars
latex2img batch eqs.jsonl -o out/ --workers 4 --wrap-text 16

# synthetic training data: 5 randomized variants per equation, reproducible
latex2img batch eqs.txt -o out/ --variants 5 --seed 42 \
  --font-pool fonts/ --scale-range 1.0,3.0 --color-mode random

# random formulas (text only, one per line) -> render them with batch
latex2img amok 1000 --seed 7 --lang vi -o rand.txt
latex2img batch rand.txt -o out/ --variants 2

# check that Chromium and the vendored MathJax assets are available
latex2img doctor
```

| Flag | Default | Applies to | Meaning |
| --- | --- | --- | --- |
| `-o, --output` | `out.png` / `out/` | render, batch | Output file (render) or directory (batch) |
| `-f, --format` | `png` | both | `png`, `svg`, `pdf` (svg for debugging; pdf reserved for future Tectonic, exit 2 in v1) |
| `--backend` | `mathjax` | both | `mathjax`, `tectonic` |
| `--lang` | `vi` | both | Selects font stack and auto-text rules: `en`, `vi`, `zh`, `ja`, `ko`, … |
| `--font` | from lang map | both | Font file path or family name; overrides lang map |
| `--scale` / `--dpi` | `2.0` / `300` | both | PNG resolution via device scale factor; `--dpi` is accepted and ignored (reserved for future Tectonic) |
| `--display/--inline` | display | both | Display vs inline math style |
| `--wrap-text N` | `0` (off) | both | Wrap `\text{}` runs longer than N chars into stacked lines |
| `--wrap-align` | `c` | both | `l`, `c`, `r` alignment of wrapped text lines |
| `--wrap-valign` | `c` | both | `c`, `t`, `random` vertical alignment of stacked names (see Layout) |
| `--wrap-eq N` | `0` (off) | both | Break equation at top-level `=`/operators when token width > N |
| `--auto-text/--no-auto-text` | on | both | Wrap bare non-ASCII letter runs in math mode into `\text{}` |
| `--color`, `--bg` | `#000000`, `transparent` | both | Foreground and background |
| `--padding` | `4` (px) | both | Padding after tight trim; must be ≥ 0 |
| `--workers` | `1` | batch | Concurrent Chromium pages |
| `--timeout` | `10` (s) | both | Per-equation render timeout |
| `--continue-on-error/--fail-fast` | continue | batch | Batch error policy |
| `--config` | auto-discover | both | Path to TOML config |
| `--keep-temp` | off | both | Keep the rendered `.tex` and raw (untrimmed) output in a temp dir, path printed to stderr |
| `-v, --verbose` | off | both | Debug logging to stderr |

Batch flags for training data (details in the Randomization section):

| Flag | Default | Meaning |
| --- | --- | --- |
| `--variants K` | `1` | Randomized renders per equation |
| `--seed S` | `0` | Base seed; each sample's RNG = hash(seed, id, k), independent of worker order |
| `--font-pool` (repeatable) | lang map font only | Font files or dirs to sample text fonts from |
| `--math-font-pool` (repeatable) | backend default | MathJax 4.1 math fonts to sample (see Randomization) |
| `--scale-range LO,HI` | off (fixed `--scale`) | Scale sampled log-uniform in \[LO, HI\] |
| `--color-mode` | `fixed` | `fixed`, `random`, `palette` |
| `--palette FILE` | none | fg/bg color pairs for `palette` mode |
| `--min-contrast` | `4.5` | Minimum fg/bg contrast ratio; resample until met |
| `--white-bg-prob` | `0.5` | `random` color mode: probability of a white background |
| `--valign-t-prob` | `0.5` | `--wrap-valign random`: probability of `t` |
| `--wrap-text-range LO,HI` | off | Wrap width sampled per sample (integer); overrides `--wrap-text` |
| `--wrap-eq-range LO,HI` | off | Same for `--wrap-eq` |
| `--padding-range LO,HI` | off | Padding (px) sampled per sample (integer, ≥ 0); overrides `--padding`; recorded as `params.padding` |
| `--label-normalize` | `none` | `none`, `canonical` (see Output) |
| `--label-source` | `rendered` | `rendered` = LaTeX after preprocessing (matches the image); `input` = as given |
| `--label-files/--no-label-files` | off | Also write `out/labels/<id>.tex` beside images |
| `--skip-existing/--overwrite` | skip-existing | Resume interrupted runs. Skipped images are not re-rendered, but their manifest rows are rebuilt (preprocessing and sampling are deterministic) |
| `--manifest PATH` | `out/manifest.jsonl` | Manifest location; `-` streams JSONL to stdout. Written to `PATH.tmp` and renamed on completion |

Stdout is reserved for machine output: `render` prints the output path; `amok` prints formulas unless `-o` is given; `batch` prints nothing unless `--manifest -` streams manifest JSONL to stdout. `batch` draws a progress bar (rich) on stderr, only when stderr is a terminal; log lines print above it.

`--help` groups options into panels (Typer `rich_help_panel`): Output, Text & fonts, Style, Wrapping, Randomization, Labels & manifest, Run & debug.

## Input, multilingual text, multi-line wrapping

### Input formats

- Positional arg or `-` for stdin: one equation, no `$` delimiters (strip `$…$`, `$$…$$`, `\[…\]` if present).
- `.txt`: one equation per line, blank lines and `#` comments skipped; ids = line numbers (zero-padded, e.g. `000123`).
- `.jsonl`: one object per line; `id` required to be unique; per-item fields override CLI flags.

```json
{"id": "eq_001", "latex": "P = \\text{giá đất nông nghiệp} \\times S", "lang": "vi", "wrap_text": 12, "variants": 3, "format": "png"}
```

### Unicode and language handling

1. **NFC normalization** of all input. Vietnamese text pasted from PDFs/Word often arrives as NFD (base letter + combining marks); some fonts position stacked marks (e.g. ệ, ố) badly in that form.
2. **Auto-text**: words in math mode that contain at least one non-ASCII letter (`\p{L}` outside `\text{}`, `\mathrm{}`, `\operatorname{}`, `\ml{}`) are wrapped in `\text{}`. A word is a whole letter run including ASCII letters, so `nông` becomes `\text{nông}`, not `n\text{ô}ng`. Consecutive such words separated only by whitespace become one group (`giá đất` → `\text{giá đất}`), since math mode would drop the spaces. Math italic fonts have no Vietnamese glyphs.
3. **Font map** by `--lang` (overridable in config). Fonts are vendored or resolved to a file path so renders are deterministic:

| Lang | Default font (text) |
| --- | --- |
| `en`, `vi` | Noto Serif |
| `zh` | Noto Serif CJK SC |
| `ja` | Noto Serif CJK JP |
| `ko` | Noto Serif CJK KR |
| other | Noto Serif + fallback list |

Noto Serif Regular is vendored in `assets/fonts/`. CJK fonts are **not** vendored (size): the defaults point at the system collection `/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc` (Debian/Ubuntu `fonts-noto-cjk`). Chromium's `@font-face` cannot select one face from a `.ttc`, so the wanted face is extracted with fontTools once and cached in `~/.cache/latex2img/fonts/`. Font specs accept `file.ttc#Family Name` to pick the face. A bare family name (no file) is resolved through `fc-match`, which is machine-dependent; pass a file path for determinism.

Math glyphs stay in the MathJax math font (newcm by default, or the sampled one); only `\text{}` content uses the language font.

### Multi-line long variable names

The preprocessor parses LaTeX with a brace-aware tokenizer (not regex), finds every `\text{…}` group, and greedily word-wraps its visible text at `--wrap-text N` characters (grapheme count, not code points). Each wrapped group becomes a single-column `matrix`/`array`, which MathJax renders without any wrapping logic of its own.

Input:

```latex
\text{price of agricultural land} = \text{tax} \times \text{dollars per square meter}
```

After preprocessing with `--wrap-text 12 --wrap-align c`:

```latex
\begin{matrix}\text{price of}\\\text{agricultural}\\\text{land}\end{matrix} = \text{tax} \times \begin{matrix}\text{dollars per}\\\text{square meter}\end{matrix}
```

Rules:

- `--wrap-align l|r` emits `\begin{array}{l}` / `{r}` instead of `matrix`.
- A single word longer than N is never split.
- Manual breaks: `\\` inside `\text{}` is not valid LaTeX, so the tool accepts a custom macro `\ml{price of \\ agricultural land}` and expands it to the same stacked form. Wrapping by width is skipped for `\ml`; to guarantee that, `\text{}` wrapping runs **before** `\ml` expansion.
- `\text{}` whose content contains commands, braces or `$` is left unwrapped (shortcut; parse it if this becomes common).
- `\text{}` nested inside `\frac`, sub/superscripts is wrapped the same way; inherits the local math style.
- Vertical alignment: stacked names are centered on the math axis by default (`matrix` behaviour). `--wrap-valign c|t|random`: c = centered on the math axis (matrix), t = first line on the baseline of the surrounding math (`\begin{array}[t]{c}`), random = picked per sample (see Randomization).

### Whole-equation wrapping (`--wrap-eq N`)

Estimated width = sum of token widths (`\text` = grapheme count, symbols = 1, `\frac` = max of num/den). When it exceeds N, split at depth-0 `=`, `+`, `-`, `\times`, `\cdot` (also `<`, `>`, `\leq`, `\geq`, `\neq`, `\approx`, `\equiv` as relations) into `\begin{aligned}` with `&=` on the first relation; continuation lines start with `&{}` so a leading `+`/`-` keeps binary spacing. A sign directly after another operator or at the start is unary and never a split point. Splitting is refused inside `\left…\right` pairs and environments; an environment counts as one atom whose width is its widest row. Equations that cannot be split, or that already contain top-level `&` or `\\`, are emitted unwrapped with a warning.

Width is measured in characters (grapheme count), for both `--wrap-text` and `--wrap-eq`. No render-and-measure pass: wrapping stays backend-independent and costs nothing per sample. Visible line widths vary with glyph widths and the sampled font, which is acceptable variety for training data \[Inference\].

## Randomization (synthetic training data)

Each equation renders `--variants K` times; each variant samples font, scale and colors from its own RNG seeded by `hash(seed, id, k)`, so any sample is reproducible alone and output does not depend on `--workers`. Sampled values go into the manifest's `params`.

### Font

- **Text font** (`\text{}` content): sampled from `--font-pool`. Before sampling, fonts are filtered by glyph coverage of the equation's text characters (cmap check via `fontTools`), so a Vietnamese label never lands on a font missing ệ/ừ. No covering font → fall back to the lang-map font and add a warning.
- **Math font**: sampled from `--math-font-pool`, a subset of MathJax 4.1's 11 fonts (newcm default, asana, bonum, dejavu, fira, modern, pagella, schola, stix2, termes, tex), chosen with `output.font` when MathJax loads ([font docs](https://docs.mathjax.org/en/v4.1/output/fonts.html)). The math font is fixed when a page loads, so pages are pooled per (math font, scale) \[Verified\].
- MathJax backend loads each text font once per page with the `FontFace` API under its own family name (`L2I_<key>`) and passes that family to `tex2svgPromise`; switching font needs no page reload \[Verified\].

### Scale

- `--scale-range LO,HI`, log-uniform. MathJax: per-sample `device_scale_factor` needs a new browser context, so the pool keeps one context per scale bucket (e.g. 8 buckets across the range) and snaps to the nearest \[Inference: avoids context churn\].
- `--padding-range LO,HI` samples the padding per sample (integer px, uniform) so margins vary; recorded as `params.padding`.

### Color

- `fixed`: `--color` / `--bg` as before.
- `random`: fg and bg sampled in HSL; resample until contrast ratio ≥ `--min-contrast` (WCAG formula). 50% of samples keep a white bg by default (`--white-bg-prob`), since real inputs are mostly black-on-white \[Inference\].
- `palette`: sample a pair from `--palette` (JSON list of `{fg, bg}`).
- PNG background is always composited (no transparency) in training mode, so the VLM never sees an alpha channel.

### Layout

- Vertical alignment of stacked `\text{}` names: with `--wrap-valign random`, each sample picks `c` (centered, `matrix`) or `t` (first line on the baseline, `\begin{array}[t]{c}`) with probability `--valign-t-prob` (default `0.5`). One choice per sample, applied to every stacked name in that equation, so a single image never mixes the two.
- The choice is applied in the preprocessor, so `label` (`latex_rendered`) carries the exact environment shown in the image, and `params.wrap_valign` records it.
- \[Verified\] MathJax 4.1.3 supports the `[t]` position argument on `array` (golden test `test_array_t_position_supported`); no `aligned` fallback needed.
- Wrap width: `--wrap-text-range LO,HI` samples N uniformly (integer) per sample, e.g. `8,24`; `0` in the range means "no wrap" for that sample. Overrides `--wrap-text`. One N per sample, used for every `\text{}` group in that equation; recorded as `params.wrap_text`. Same for `--wrap-eq-range` if equation wrapping is on.

### Output naming

With `--variants > 1`, images are `out/images/{id}_{k:02d}.png`; each variant is its own manifest row sharing the same `label`.

```json
{"id": "eq_001_03", "source_id": "eq_001", "variant": 3, "image": "images/eq_001_03.png", "label": "...", "params": {"text_font": "NotoSerif-Italic.ttf", "math_font": "mathjax-stix2", "scale": 2.37, "fg": "#1b2a4a", "bg": "#f4efe6", "wrap_text": 12, "wrap_eq": 0, "wrap_valign": "t", "padding": 9, "seed": 918273}, "error": null}
```

Adds `fonttools` to core dependencies.

## Random formulas (`amok`)

`amok COUNT` writes COUNT random formulas, one per line, to stdout or `-o FILE`. Output is plain `.txt` for `batch`; `amok` never renders. Line k uses its own RNG `sample_rng(seed, "amok", k)`, so output is reproducible and independent of COUNT.

| Flag | Default | Meaning |
| --- | --- | --- |
| `-o, --output` | stdout | Output `.txt` file |
| `--seed` | `0` | Base seed |
| `--lang` | `en` | `\text{}` word list: `en`, `vi`, `zh` (others fall back to `en`) |
| `--depth` | `3` | Max nesting depth (grammar mode) |
| `--from FILE` | off | Mutate a `.txt`/`.jsonl` corpus instead of using the grammar; line k mutates item `k mod N` |

- **Grammar (default)**: `lhs REL expr`. `lhs` is an atom or `\text{words}`; `REL` ∈ `= \leq \geq \approx < >`. `expr` picks (weighted) an atom, a binary op (`+ - \times \cdot`), `\frac`, `\sqrt`, `^{}`, `_{}`, `_{}^{}`, `\left(\right)`, `\sin/\cos/\log/\ln/\exp`, `\sum_{i=1}^{n}` or `\int_{0}^{T} … \, dt`, until `--depth` runs out. Atoms: a letter, a Greek letter, a number (integer, decimal or percent) or `\text{}` with 1–2 words.
- **Mutation (`--from`)**: tokenizes each formula; ASCII letters are remapped consistently within one formula, digits and binary ops are randomized, and each `\text{}` argument is replaced with random words. Control words, braces and the arguments of `\begin`, `\end`, `\operatorname`, `\mathrm` are kept, so structure and brace balance are preserved.
- Usage errors (exit 2): COUNT < 1, `--depth` < 0, unreadable or empty `--from` file.
- `examples/amok.sh` generates en/vi/zh formulas (one seed per language) and renders them with `batch`.

\[Verified\] Tests render 50 generated and mutated formulas through MathJax without errors, and a 20-formula `amok` → `batch` run gave ok=20 failed=0. Grammar output is structurally valid but not semantically realistic \[Inference\]; use `--from` when realism matters.

## Architecture

Pipeline per job (straight run, backend-agnostic except step 4):

1. **Load**: CLI args / txt / JSONL → `RenderJob` objects, merged with config defaults.
2. **Normalize**: strip delimiters, NFC, auto-text.
3. **Wrap**: `\text{}` wrapping, `\ml` expansion (in that order, so `\ml` lines are never re-wrapped), optional equation wrapping. Preprocessing errors (e.g. unbalanced braces) skip this step with a warning and let the renderer report the real error.
4. **Render**: backend produces SVG, or PNG via element screenshot.
5. **Post-process**: tight trim, padding, background.
6. **Write**: output file + manifest row.

```text
latex2img/
├── pyproject.toml
├── pixi.lock
├── src/latex2img/
│   ├── __init__.py
│   ├── __main__.py          # python -m latex2img
│   ├── cli.py               # typer app: render, batch, amok, doctor
│   ├── amok.py              # random formula grammar + corpus mutation
│   ├── config.py            # dataclasses + TOML loading, precedence CLI > env > file > defaults
│   ├── models.py            # RenderJob (+ math_font), RenderResult (+ timed_out), OutputFormat
│   ├── io.py                # input readers (arg/stdin/txt/jsonl), manifest writer
│   ├── fonts.py             # lang -> font file resolution, cmap coverage
│   ├── randomize.py         # per-sample RNG, font/scale/color/layout sampling
│   ├── labels.py            # --label-normalize
│   ├── pipeline.py          # sample building + randomization, run loop, manifest rows (shared by render/batch)
│   ├── preprocess/
│   │   ├── tokenizer.py     # brace-aware LaTeX tokenizer
│   │   ├── normalize.py     # delimiters, NFC, auto-text
│   │   └── wrap.py          # \text wrapping, \ml, equation wrapping
│   ├── renderers/
│   │   ├── base.py          # Renderer protocol, registry (tectonic.py slots in here later)
│   │   └── mathjax.py       # Playwright + vendored MathJax 4.1
│   ├── postprocess.py       # trim, pad, background composite (Pillow)
│   └── assets/
│       ├── mathjax/         # vendored MathJax 4.1 components
│       ├── @mathjax/        # vendored math font packages
│       ├── page.html        # render page with @font-face
│       └── fonts/           # vendored OFL text fonts (Noto Serif, ...)
└── tests/
```

Core types and renderer protocol (async). The protocol stays even with one backend, so Tectonic can be added later without touching the pipeline:

```python
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


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
    timed_out: bool = False  # CLI maps to exit 4

    @property
    def ok(self) -> bool:
        return self.error is None


@runtime_checkable
class Renderer(Protocol):
    name: str
    supported_formats: frozenset[OutputFormat]

    async def __aenter__(self) -> Renderer: ...  # start browser / check binary

    async def __aexit__(self, *exc: object) -> None: ...

    async def render(self, job: RenderJob) -> RenderResult: ...
```

MathJax backend core (one browser, pages pooled per (math font, scale); each page loads `page.html` once). The render function lives in `page.html`; Python calls it:

```javascript
window.l2iRender = async ({tex, display, family, color}) => {
  MathJax.texReset();
  const node = await MathJax.tex2svgPromise(tex, {display, family});  // family -> \text{} font
  const err = node.querySelector('[data-mml-node="merror"]');
  if (err) return {error: err.getAttribute("title") || err.textContent};  // TeX errors are values
  const host = document.getElementById("host");
  host.style.color = color;
  host.replaceChildren(node);
  const svg = node.querySelector("svg").cloneNode(true);
  svg.setAttribute("color", color);  // MathJax paints with currentColor
  return {svg: svg.outerHTML};
};
```

```python
async def _render_on_page(self, page: Page, job: RenderJob) -> RenderResult:
    await page.evaluate("([f, u]) => l2iSetFont(f, u)", [family, font_url])  # FontFace, cached per page
    out = await page.evaluate("(args) => l2iRender(args)", {...})
    if "error" in out:
        return RenderResult(job.id, None, job.fmt, error=out["error"])
    if job.fmt is OutputFormat.SVG:
        return RenderResult(job.id, out["svg"].encode(), job.fmt)
    png = await page.locator("#host svg").first.screenshot(omit_background=True)  # nested <svg> exists
    return RenderResult(job.id, png, job.fmt)
```

Each scale gets its own browser context (`device_scale_factor`). A semaphore limits concurrent renders to `--workers`; idle pages are kept per (math font, scale) and evicted when more than `max(4, 2 × workers)` pages exist. PNGs are always screenshotted transparent; the background is composited in post-processing so trimming is uniform. A timed-out page is closed rather than reused. \[Verified\] `tex2svgPromise` and the `merror` layout match MathJax 4.1.3 (renderer contract tests).

## Outputs, config, errors

### Output

| Format | MathJax |
| --- | --- |
| PNG | Element screenshot at `device_scale_factor`, transparent by default. Training mode (`--variants > 1` or `--color-mode` ≠ `fixed`) always composites a background (white if none) |
| SVG | MathJax SVG (text as `<text>`, font-dependent) |
| PDF | Not supported (exit 2) |

Post-process for PNG: tight-trim to the non-background bbox with Pillow, then add `--padding`. Batch images go to `out/images/{id}.{ext}` (`{id}_{k:02d}` with variants). `id` comes from JSONL or the txt line number; when missing, `sha1(latex + render options)[:12]`.

Batch writes `manifest.jsonl` next to outputs:

```json
{"id": "eq_001", "source_id": "eq_001", "variant": 0, "source": "eqs.jsonl:1", "image": "images/eq_001.png", "label": "...", "latex_in": "...", "latex_rendered": "...", "backend": "mathjax", "width": 412, "height": 96, "params": {...}, "error": null, "warnings": []}
```

`latex_rendered` stores the post-preprocessing source, so wrapping decisions are inspectable and reproducible.

For image→LaTeX VLM training, `label` is the target text and `image` is relative to the output dir. Default `--label-source rendered`: wrapping rewrites `\text{…}` into `matrix`, so only the rendered source matches what the image shows. Failed jobs stay in the manifest with `error` set and no `image`; filter them out when building the training set.

`--label-normalize none|canonical` (default `none`) controls the label string. `none` = the rendered source as-is. `canonical` runs these token-level rewrites after preprocessing, using the same brace-aware tokenizer:

1. Whitespace: one space between tokens only where TeX needs it (after a control word before a letter); none elsewhere.
2. Scripts: every `^`/`_` argument braced (`x^2` → `x^{2}`).
3. Redundant braces removed (`{x}+{y}` → `x+y`), except script and command arguments.
4. Synonym commands mapped to one spelling (`\le` → `\leq`, `\ge` → `\geq`, `\ne` → `\neq`, `\to` → `\rightarrow`); the map lives in config (`[label] synonyms`).

Conservative choices: text-mode arguments (`\text{…}` etc.) are copied verbatim; empty groups `{}` and groups containing control words, `&` or `\\` keep their braces; a multi-token group before `^`/`_` keeps its braces (`{a+b}^2`); a script whose argument is a command taking arguments (`x^\frac12`) is not re-braced. If the label cannot be tokenized (unbalanced braces), it is kept raw with a warning.

Normalization never changes the image: it runs on the label only, after the render source is fixed. With `canonical`, the manifest keeps both `label` (normalized) and `label_raw` (as rendered). Tests assert that rendering `label` and `label_raw` gives the same PNG.

### Config

Precedence: CLI flag > per-item JSONL field > env (`LATEX2IMG_*`) > `--config` file > `./latex2img.toml` > `[tool.latex2img]` in `pyproject.toml` > defaults.

```toml
format = "png"
lang = "vi"
scale = 2.0
wrap_text = 16
wrap_align = "c"

[fonts]
vi = "assets/fonts/NotoSerif-Regular.ttf"
ja = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"

[mathjax]
extensions = ["mhchem"]
macros = { R = "\\mathbb{R}" }
math_fonts = ["mathjax-newcm", "mathjax-stix2", "mathjax-pagella"]
```

`macros` is passed to MathJax as `tex.macros`; the preprocessor never expands them, so labels keep the macro names.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | All jobs rendered |
| 1 | One or more jobs failed (batch with continue-on-error) or the single render failed |
| 2 | Usage error (bad flag, unsupported format for backend) |
| 3 | Backend unavailable (no Chromium, missing MathJax assets) |
| 4 | Timeout (single render) |

Error messages go to stderr with the job id and MathJax's `merror` title. Browser crash → restart browser once, retry the in-flight jobs, then fail them \[Unverified: implemented, never triggered in tests\]. Malformed LaTeX in a batch is an error row (exit 1), not a usage error.

## Project setup (pixi + uv), testing, offline deployment

### Toolchain: pixi + uv, conda-forge only

Pixi owns the environment and resolves conda-forge packages first, then hands PyPI deps to uv; both land in one `pixi.lock` ([pixi](https://pixi.prefix.dev/latest/), [Conda & PyPI](https://pixi.prefix.dev/latest/concepts/conda_pypi)). `pyproject.toml` is the only manifest. Channel: `conda-forge`, nothing else. Platform: `linux-64`.

| Component | Source | Installed by |
| --- | --- | --- |
| Python 3.10 (floor of `>=3.10`) | conda-forge `python` | pixi |
| `nodejs` (vendoring only) | conda-forge | pixi, `vendor` env |
| typer, pillow, regex, fonttools, playwright | PyPI | pixi → uv |
| ruff, pytest, pytest-asyncio | PyPI | pixi → uv, `dev` feature |
| Chromium | Playwright download | `pixi run install-browser` |
| MathJax 4.1 + font packages | npm, vendored into `assets/` | `pixi run -e vendor vendor-mathjax` |

### pyproject.toml

Version floors are minimums; `pixi.lock` pins exact versions (resolved at implementation: typer 0.29.0, pillow 12.3.0, regex 2026.9.29, fonttools 4.65.0, playwright 1.65.0, pytest 9.2.0, ruff 0.17.4, python 3.10.22).

```toml
[project]
name = "latex2img"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "typer>=0.12",
    "pillow>=10.0",
    "regex>=2024.0",  # \p{L} and grapheme (\X) matching for auto-text and wrap
    "fonttools>=4.50",  # cmap coverage check for font randomization
    "playwright>=1.45",  # MathJax backend (only backend in v1)
    "tomli>=2.0; python_version < '3.11'",
]

[project.scripts]
latex2img = "latex2img.cli:app"

[dependency-groups]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "ruff"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/latex2img"]

# ---------------- pixi ----------------
[tool.pixi.workspace]
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]  # conda-forge
python = "3.10.*"
# future Tectonic backend: tectonic, poppler

[tool.pixi.pypi-dependencies]  # resolved by uv
latex2img = { path = ".", editable = true }

[tool.pixi.feature.vendor.dependencies]
nodejs = ">=20"

[tool.pixi.environments]
default = { features = ["dev"], solve-group = "default" }  # dev = [dependency-groups].dev
prod = { features = [], solve-group = "default" }
vendor = { features = ["vendor"], no-default-feature = true }

[tool.pixi.tasks]
install-browser = "playwright install chromium"
doctor = "latex2img doctor"
lint = "ruff check . && ruff format --check ."
fmt = "ruff format ."
test = "pytest"
# offline bundle: conda+PyPI deps via pixi-pack, latex2img itself as a wheel (pixi-pack only packs wheels).
# target: pixi-unpack dist/latex2img-env.tar && uv pip install --offline --no-deps --python env/bin/python dist/*.whl
pack = "mkdir -p dist && pixi exec pixi-pack -e prod -p linux-64 --ignore-pypi-non-wheel -o dist/latex2img-env.tar pyproject.toml && pixi exec uv build --wheel -o dist"

[tool.pixi.feature.vendor.tasks]
vendor-mathjax = "rm -rf build/npm src/latex2img/assets/mathjax src/latex2img/assets/@mathjax && npm install --no-save --prefix build/npm mathjax@4.1.3 @mathjax/mathjax-newcm-font@4.1.3 @mathjax/mathjax-stix2-font@4.1.3 @mathjax/mathjax-pagella-font@4.1.3 @mathjax/mathjax-mhchem-font-extension@4.1.3 && cp -r build/npm/node_modules/mathjax build/npm/node_modules/@mathjax src/latex2img/assets/ && cd src/latex2img/assets/@mathjax && rm -rf */cjs */mjs */chtml */chtml.js */tex-*.js"  # browser loads only svg.js + svg/

[tool.ruff]
line-length = 120
extend-exclude = [".pixi", "build", "src/latex2img/assets"]
# Flake8 - E, F
# pycodestyle - W
# flake8-builtins - A
# Pylint - PLC, PLE, PLW
# isort - I
select = ['E', 'F', 'W', 'A', 'PLC', 'PLE', 'PLW', 'I']

[tool.ruff.format]
# Like Black
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

Notes:

- `features = ["dev"]` relies on pixi mapping `[dependency-groups]` to features \[Verified: pixi 0.84.2\].
- `tomli` is a runtime dependency because Python 3.10 has no `tomllib`.
- `vendor-mathjax`: add one `@mathjax/mathjax-<name>-font` per math font in the randomization pool, plus `@mathjax/mathjax-<ext>-font-extension` for TeX extensions that ship one (mhchem). Font packages follow the MathJax version (4.1.3) \[Verified\]. Output is committed, so normal installs need no Node.
- `[tool.uv.sources]` is ignored in the main manifest under pixi; keep path/git sources in `[tool.pixi.pypi-dependencies]` ([pyproject guide](https://pixi.prefix.dev/latest/python/pyproject_toml)).
- A package listed on both sides is installed from conda-forge ([Conda & PyPI](https://pixi.prefix.dev/latest/concepts/conda_pypi)). Keep playwright, pillow, fonttools PyPI-only.
- Ruff config as given. Ruff 0.17 warns that top-level `select` is deprecated in favour of `[tool.ruff.lint]` \[Verified\]; `A` does not flag `RenderJob.id` \[Verified\].
- `extend-exclude` is required: without a git repo ruff does not read `.gitignore`, and `ruff format .` would otherwise reformat the packages inside `.pixi/`.

### Daily use

```bash
curl -fsSL https://pixi.sh/install.sh | sh   # once per machine
pixi install
pixi run install-browser
pixi run -e vendor vendor-mathjax          # once per MathJax bump; commit assets/
pixi run doctor
pixi run lint
pixi run test
pixi run pack                              # offline bundle into dist/
```

uv-only path (no conda), same `pyproject.toml`. With MathJax as the only backend nothing needs conda-forge at runtime, so this covers everything except vendoring MathJax \[Verified: uv 0.13.6, clean copy, 47 tests pass\]:

```bash
uv sync
uv run playwright install chromium
uv run pytest
```

Plain `pip install .` into a Python ≥ 3.10 venv, `uv pip install .`, and `uv tool install --with-executables-from playwright .` also work \[Verified\]. The test suite passes on Python 3.10, 3.11, 3.12, 3.13 and 3.14 \[Verified\]; see README.md.

### Testing

- **Preprocessor (pure, most coverage)**: tokenizer brace handling, escaped braces, nested `\text` in `\frac`/scripts, NFC/NFD Vietnamese, auto-text boundaries, wrap widths 0/1/long words, `\ml` expansion, equation splits refused inside `\left…\right`. Assert on output LaTeX strings.
- **Golden images**: 27 fixtures in `tests/golden/` (English, Vietnamese with stacked diacritics like ệ ổ ừ, CJK, long names, matrices, one per math font in the pool). Compare PNG by size ±2 px and mean abs pixel diff < 8, not byte equality. Regenerate with `UPDATE_GOLDEN=1`; missing goldens are written on first run, so review new ones by eye.
- **Padding**: trim-then-pad sizes, fixed `--padding`, `--padding-range` border equals `params.padding`, negative values exit 2.
- **Renderer contract**: written against the `Renderer` protocol, not MathJax internals, so a future Tectonic renderer reuses it. Error cases (`\frac{`, unknown macro) must yield `RenderResult.error`, not exceptions.
- **CLI**: `typer.testing.CliRunner` for exit codes and manifest content.
- **amok**: same seed → same lines, balanced braces, non-empty `\text{}`, mutation keeps control words, and a MathJax smoke render of generated formulas.

### Offline / airgapped deployment

1. **Environment**: on a connected x86\_64 host, `pixi run pack` ([Pixi Pack](https://pixi.prefix.dev/latest/deployment/pixi_pack/)). \[Verified: pixi-pack 0.7.12\] pixi-pack packs PyPI dependencies only as wheels and refuses the editable `latex2img` itself, so the task packs the `prod` env with `--ignore-pypi-non-wheel` (`dist/latex2img-env.tar`, 105 MiB) and builds latex2img as a separate wheel (`dist/latex2img-0.1.0-py3-none-any.whl`, 11 MB, includes MathJax and Noto Serif). On the target:
   ```bash
   pixi-unpack latex2img-env.tar
   uv pip install --offline --no-deps --python env/bin/python latex2img-0.1.0-py3-none-any.whl
   source activate.sh
   ```
   Verified in a network namespace with no network (`unshare -rn`): `doctor` passes and a Vietnamese equation renders. Not verified on a separate machine. Alternative: build a container image from the pixi env ([Container](https://pixi.prefix.dev/latest/deployment/container/)).
2. **MathJax**: already vendored in `assets/` by `vendor-mathjax`; `output.fontPath` points at the local copy, no CDN at runtime.
3. **Chromium**: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers pixi run install-browser` on the connected host; copy `/opt/pw-browsers` and set the same env var on the target. System libs for Chromium still come from the target's OS packages.
4. **Fonts**: Noto Serif is vendored in the wheel (OFL), resolved by path. CJK defaults come from the target's `fonts-noto-cjk` package; copy the `.ttc` (or `~/.cache/latex2img/fonts/`) if the target lacks it.

## Future work: Tectonic backend

Add Tectonic as a second `Renderer` when MathJax cannot render needed packages (failures show up as `error` rows in the manifest), or when renders closer to TeX-typeset documents are wanted. v1 keeps the hooks: the `Renderer` protocol, `--backend`, `OutputFormat.PDF` and `backend` in the manifest. The no-mixing rule stays: one backend per run.

- **Renderer**: one `.tex` per job in a temp dir via `asyncio.create_subprocess_exec`, process pool sized by `--workers`. Batch N equations into one `standalone` multi-page doc if per-run overhead dominates \[Inference\].
- **Fonts**: `fontspec` + the lang font file (Noto Serif for en/vi; `xeCJK` for zh/ja/ko). Math fonts via `unicode-math` + `\setmathfont` (Latin Modern Math, STIX Two Math, TeX Gyre Math fonts) \[Unverified: availability in the Tectonic bundle\].
- **Output**: PDF native; PNG via `pypdfium2` at DPI = 150 × scale; SVG via `pdftocairo -svg`, which outlines glyphs, so the SVG is portable even with Vietnamese text.
- **Environment**: add `tectonic` and `poppler` to `[tool.pixi.dependencies]` (conda-forge ships tectonic 0.15.0 for linux-64, [anaconda.org](https://anaconda.org/conda-forge/tectonic/files?type=conda)) and `pypdfium2` to the PyPI deps.
- **Offline**: pre-warm Tectonic's package cache with every allowed package and run with the only-cached flag \[Unverified: cache path and flag name per Tectonic version\].
- **Tests**: run the existing renderer-contract suite and golden images against it.

Template:

```latex
\documentclass[border=4pt,varwidth]{standalone}
\usepackage{amsmath,amssymb}
\usepackage{fontspec}
\setmainfont{((FONT_FILE))}[Path=((FONT_DIR))/]
((EXTRA_PREAMBLE))
\begin{document}
\(\displaystyle ((LATEX))\)
\end{document}
```

Placeholders use `((…))` to avoid clashing with LaTeX braces; substitution is plain string replace, not `str.format`.

## Open questions

- [ ] Is portable SVG with Vietnamese text required? If yes, Tectonic is the only backend that outlines glyphs; MathJax SVG would need a text-to-path step. Tentative: ship PNG only, so portable SVG is not required; SVG/PDF stay available for debugging.
- [ ] Packages needed beyond amsmath (mhchem, physics, cancel)? Decides whether MathJax coverage is enough as default. With MathJax as the only v1 backend, unsupported packages show up as error rows in the manifest; their count decides when the Tectonic future work is needed.
- [x] Label normalization: keep `label` exactly as rendered, or canonicalize it (whitespace, `x^2` vs `x^{2}`, redundant braces) so equivalent LaTeX maps to one target string? Decided: an option, --label-normalize none|canonical (default none).
- [x] Backend mix for training data: render only with MathJax (fast), or send a fraction of samples through Tectonic for renderer diversity? If mixed, what ratio? Decided: no mixing. One backend per run (--backend), never randomized per sample.
- [x] Image size for the VLM: should the tool enforce a max side or aspect-ratio buckets, or leave resizing to the dataloader? Decided: the dataloader handles it. The tool writes tight-trimmed images at the sampled scale; width/height are in the manifest.
- [x] Randomize `--wrap-text N` per sample (e.g. uniform in a range) for line-break variety, or keep one N per run? Decided: randomized per sample (--wrap-text-range).
- [x] Use case: docs/report images, or synthetic training data (e.g. for OCR/layout)? Decided: synthetic training data for an image→LaTeX VLM; txt/JSONL input; font/scale/color randomization specced (no bboxes needed).
- [x] Wrap width unit: characters (v1) or rendered pixels (v2, MathJax measurement)? Decided: characters (grapheme count); no pixel measurement.
- [x] Stacked names: centered on math axis (default `matrix`) or first-line baseline aligned with `=`? Decided: randomized per sample (--wrap-valign random).
- [x] Target hosts: x86\_64 only, or also Jetson/arm64? Affects Chromium and Tectonic availability. Decided: x86\_64 (linux-64) only.
- [x] MathJax version to pin: decided, 4.1 (stable).

## Implementation notes (v0.1.0)

Deviations from the original plan, and why:

- **Auto-text wraps whole words** containing a non-ASCII letter, and joins adjacent ones. The literal rule (non-ASCII runs only) splits `nông` into `n\text{ô}ng`.
- **`\text` wrapping runs before `\ml` expansion.** In the planned order the stacked `\ml` lines were re-wrapped by width.
- **`\text{}` with commands, braces or `$` inside is not wrapped.**
- **Text font needs the `family` conversion option**; `@font-face` + `mtextInheritFont` alone has no effect on `tex2svgPromise` output.
- **`noundefined` removed** so unknown macros are errors.
- **Extra fields and flags:** `RenderJob.math_font`, `RenderResult.timed_out`, `--wrap-valign`, `--white-bg-prob`, `--valign-t-prob`, `--padding-range`, `--manifest`; `pipeline.py` module; `tomli` dependency.
- **CJK fonts not vendored**; extracted from the system `.ttc` into a cache.
- **Batch progress bar** on stderr (rich, already a typer dependency), via an `on_done` callback on `run_samples`; disabled when stderr is not a TTY.
- **pixi-pack needs the wheel workaround** described under Offline deployment.
- **`amok` subcommand added** (not in the original plan): random formula generator, text only; see "Random formulas (`amok`)".

Not implemented / not verified: `--dpi` (accepted, ignored); browser-crash restart (implemented, untested); offline install on a truly separate machine; `playwright install-deps` on a fresh OS.
