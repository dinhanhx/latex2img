# latex2img

Render LaTeX math to PNG (or SVG for debugging) from the command line. It handles Vietnamese and other Unicode text inside equations, wraps long `\text{…}` names onto stacked lines, and can generate randomized variants (fonts, scale, colors, layout) as synthetic training data for image→LaTeX models. It can also generate random formulas to feed that pipeline (`amok`).

Rendering uses MathJax 4.1.3 in headless Chromium. MathJax and the default text font ship inside the package, so rendering works fully offline once Chromium is installed.

```bash
latex2img render 'P = \text{giá đất nông nghiệp} \times S' -o out.png
```

## Requirements

- Linux x86_64
- **Python 3.10 or newer** (tested on 3.10 to 3.14)
- Chromium, installed through Playwright (step 2 below)
- Optional, for Chinese/Japanese/Korean text: the Noto CJK fonts (`sudo apt install fonts-noto-cjk`)

You do not need Node.js. MathJax is already vendored in `src/latex2img/assets/`.

## Install with uv (recommended)

If your system Python is older than 3.10, uv can download a newer one for you (`--python 3.12`, for example).

**As a command-line tool** (puts `latex2img` on your PATH, in an isolated environment):

```bash
uv tool install --with-executables-from playwright /path/to/latex2img
playwright install chromium
latex2img doctor
```

`--with-executables-from playwright` also exposes the `playwright` command from the tool's environment. This matters because Chromium must match the Playwright version latex2img was installed with.

**Into a virtual environment** (to use it from Python code or alongside other packages):

```bash
uv venv
source .venv/bin/activate
uv pip install /path/to/latex2img
playwright install chromium
latex2img doctor
```

**For development** (from a checkout, with test and lint tools):

```bash
cd latex2img
uv sync
uv run playwright install chromium
uv run pytest
```

## Install with pip

Use any Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install /path/to/latex2img        # a checkout, or the built wheel latex2img-0.1.0-py3-none-any.whl
playwright install chromium
latex2img doctor
```

If your `python3` is older than 3.10, get a newer one with `uv python install 3.12`, conda, pyenv or deadsnakes. You can also use the uv route above instead.

## Step 2: Chromium

`playwright install chromium` downloads Chromium (about 126 MiB) into `~/.cache/ms-playwright`. On a fresh machine Chromium may also need system libraries. Install them once with:

```bash
sudo "$(which playwright)" install-deps chromium
```

To keep browsers somewhere else (shared or offline machines), set `PLAYWRIGHT_BROWSERS_PATH` both when installing and when running:

```bash
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers playwright install chromium
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
```

## Check the install

```bash
latex2img doctor
```

```text
ok   MathJax assets
ok   Chromium + test render
```

Exit code 3 means the backend is unavailable. The message names the missing piece, which is usually Chromium (run `playwright install chromium`).

## Usage

```bash
# one equation -> PNG (prints the output path)
latex2img render 'E = mc^2' -o e.png

# from stdin, SVG for debugging
echo 'E = mc^2' | latex2img render - -f svg -o e.svg

# white background, more padding, wrap \text{} names longer than 12 characters
latex2img render '\text{price of agricultural land} = \text{tax} \times S' \
  --bg white --padding 10 --wrap-text 12 -o land.png

# batch: .txt (one equation per line) or .jsonl ({"id": ..., "latex": ..., per-item options})
latex2img batch eqs.jsonl -o out/ --workers 4

# training data: 5 reproducible random variants per equation
latex2img batch eqs.txt -o out/ --variants 5 --seed 42 \
  --font-pool fonts/ --math-font-pool newcm --math-font-pool stix2 \
  --scale-range 1.0,3.0 --color-mode random \
  --wrap-text-range 8,24 --wrap-valign random --padding-range 2,20
```

A batch writes `out/images/<id>.png` (or `<id>_<k>.png` with variants) and `out/manifest.jsonl`. Each manifest row has one image's label (the LaTeX actually rendered), its size, the sampled parameters and any error. Failed equations stay in the manifest with `error` set. Re-running a batch skips images that already exist (`--overwrite` to redo them). While it runs, a batch shows a progress bar on stderr (only in a terminal, so pipes and CI logs stay clean).

### Random formulas (`amok`)

`amok` prints random LaTeX formulas, one per line, in the `.txt` format `batch` reads. It does not render anything itself.

```bash
# grammar: letters, Greek, numbers, \text{} words, \frac, \sqrt, ^, _, \left(\right), \sin, \sum, \int
latex2img amok 1000 --seed 7 --lang vi --depth 3 -o rand.txt

# mutate an existing corpus: same structure, new letters, digits, operators and \text{} words
latex2img amok 1000 --from examples/input.txt --lang zh -o rand.txt

latex2img batch rand.txt -o out/ --variants 2 --lang zh
```

`--lang` picks the `\text{}` word list (`en`, `vi`, `zh`; anything else falls back to `en`). The same `--seed` gives the same lines. `examples/amok.sh [COUNT_PER_LANG] [batch args...]` generates en, vi and zh formulas into `examples/amok.txt` and renders them to `examples/amok_out/`.

See `latex2img render --help`, `latex2img batch --help` and `latex2img amok --help` for every option, grouped by topic (Output, Text & fonts, Style, Wrapping, Randomization, Labels & manifest, Run & debug).

### Manual line breaks

`\\` is not allowed inside `\text{}`, so use `\ml{…}` instead:

```bash
latex2img render '\ml{price of \\ agricultural land} = x' -o ml.png
```

### Config file

Settings are read from, lowest to highest priority: `[tool.latex2img]` in `pyproject.toml`, `./latex2img.toml`, `--config FILE`, `LATEX2IMG_*` environment variables, per-item JSONL fields, and command-line flags.

```toml
lang = "vi"
wrap_text = 16

[fonts]
vi = "/path/to/MyFont.ttf"
zh = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc#Noto Serif CJK SC"

[mathjax]
extensions = ["mhchem"]
macros = { R = "\\mathbb{R}" }
math_fonts = ["mathjax-newcm", "mathjax-stix2", "mathjax-pagella"]
```

The bundled math fonts are newcm (default), stix2 and pagella.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Everything rendered |
| 1 | At least one equation failed (bad LaTeX, unknown macro) |
| 2 | Usage error (bad flag, `-f pdf`, duplicate JSONL ids, `amok` count < 1) |
| 3 | Backend unavailable (no Chromium, missing assets) |
| 4 | Timeout (single render) |

## Offline / airgapped install

On a machine with internet access, build a wheel and download Chromium:

```bash
uv build --wheel -o dist                                              # dist/latex2img-0.1.0-py3-none-any.whl
# --python-version must match the target's Python: pillow and regex ship per-version wheels
pip download -d dist/wheels --python-version 3.12 --only-binary=:all: dist/latex2img-0.1.0-py3-none-any.whl
PLAYWRIGHT_BROWSERS_PATH=$PWD/dist/pw-browsers playwright install chromium
```

Copy `dist/` to the target. Then:

```bash
python3 -m venv .venv && source .venv/bin/activate     # same Python version as --python-version above
pip install --no-index --find-links dist/wheels dist/latex2img-0.1.0-py3-none-any.whl
export PLAYWRIGHT_BROWSERS_PATH=/path/to/dist/pw-browsers
latex2img doctor
```

Chromium's system libraries must already be installed on the target. If you use pixi, `pixi run pack` builds a pixi-pack bundle instead (see the spec, "Offline / airgapped deployment").

## Troubleshooting

- **`requires a different Python: 3.x not in '>=3.10'`**: your venv's Python is older than 3.10. Recreate it with a newer interpreter, e.g. `uv venv -p 3.12`.
- **`doctor` fails at "Chromium"**: run `playwright install chromium` with the `playwright` from the same environment as `latex2img`. If Chromium starts but crashes, install its system libraries with `playwright install-deps chromium`.
- **CJK text renders as boxes or fails with "font file not found"**: install `fonts-noto-cjk`, or point `[fonts]` at a CJK font file.
- **`Undefined control sequence \foo`**: MathJax doesn't know the macro. Define it under `[mathjax] macros`, or enable the extension that provides it.

## License notes

Bundled third-party assets: MathJax (Apache-2.0) and Noto Serif (SIL OFL 1.1).
