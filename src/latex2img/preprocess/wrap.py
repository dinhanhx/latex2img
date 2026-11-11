r"""\ml expansion, \text{} word-wrapping into stacked environments, whole-equation wrapping."""

from __future__ import annotations

from latex2img.preprocess.tokenizer import command_arg, graphemes, group_end, is_space, tokenize


def stack(lines: list[str], align: str = "c", valign: str = "c") -> str:
    r"""Stack text lines: matrix for centered/axis, array for l/r or top (baseline) alignment."""
    body = r"\\".join(r"\text{" + line + "}" for line in lines)
    if valign == "t":
        return r"\begin{array}[t]{" + align + "}" + body + r"\end{array}"
    if align == "c":
        return r"\begin{matrix}" + body + r"\end{matrix}"
    return r"\begin{array}{" + align + "}" + body + r"\end{array}"


def word_wrap(text: str, width: int) -> list[str]:
    """Greedy word wrap by grapheme count. A word longer than width is never split."""
    lines: list[str] = []
    for word in text.split():
        if lines and graphemes(lines[-1]) + 1 + graphemes(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def _rewrite_command(latex: str, command: str, fn) -> str:
    """Replace every `command{arg}` with fn(arg_source) (or keep it when fn returns None)."""
    tokens = tokenize(latex)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] == command and (arg := command_arg(tokens, i)):
            open_, close = arg
            new = fn("".join(tokens[open_ + 1 : close]))
            out.append(new if new is not None else "".join(tokens[i : close + 1]))
            i = close + 1
        else:
            out.append(tokens[i])
            i += 1
    return "".join(out)


def expand_ml(latex: str, align: str = "c", valign: str = "c") -> str:
    r"""`\ml{a \\ b}` -> stacked \text lines; manual breaks, no width wrapping."""

    def fn(arg: str) -> str:
        return stack([line.strip() for line in arg.split(r"\\")], align, valign)

    return _rewrite_command(latex, r"\ml", fn)


def wrap_text(latex: str, width: int, align: str = "c", valign: str = "c") -> str:
    r"""Wrap every \text{...} whose visible text exceeds `width` graphemes into a stacked environment."""
    if width <= 0:
        return latex

    def fn(arg: str) -> str | None:
        # shortcut: \text containing commands, groups or inline math is left unwrapped; parse it if needed
        if any(c in arg for c in "\\{}$"):
            return None
        lines = word_wrap(arg, width)
        return stack(lines, align, valign) if len(lines) > 1 else None

    return _rewrite_command(latex, r"\text", fn)


# ---------------------------------------------------------------- whole-equation wrapping

_RELATIONS = frozenset({"=", "<", ">", r"\leq", r"\geq", r"\le", r"\ge", r"\neq", r"\ne", r"\approx", r"\equiv"})
_BREAKS = _RELATIONS | {"+", "-", r"\times", r"\cdot"}
_TEXTLIKE = frozenset({r"\text", r"\mathrm", r"\operatorname", r"\textrm", r"\mbox"})


def estimate_width(tokens: list[str]) -> int:
    r"""Character-width estimate: \text = graphemes, symbols = 1, \frac = max(num, den), env = widest row."""
    width = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if is_space(tok) or tok.startswith("%") or tok in ("^", "_", "}"):
            i += 1
        elif tok == "{":
            end = group_end(tokens, i)
            width += estimate_width(tokens[i + 1 : end])
            i = end + 1
        elif tok in _TEXTLIKE and (arg := command_arg(tokens, i)):
            width += graphemes("".join(tokens[arg[0] + 1 : arg[1]]).strip())
            i = arg[1] + 1
        elif (
            tok in (r"\frac", r"\dfrac", r"\tfrac")
            and (num := command_arg(tokens, i))
            and (den := command_arg(tokens, num[1]))
        ):
            width += max(estimate_width(tokens[num[0] + 1 : num[1]]), estimate_width(tokens[den[0] + 1 : den[1]]))
            i = den[1] + 1
        elif tok == r"\begin":
            end = _env_end(tokens, i)
            body = tokens[command_arg(tokens, i)[1] + 1 : end]
            width += max((estimate_width(row) for row in _split_rows(body)), default=0)
            i = command_arg(tokens, end)[1] + 1
        elif tok in (r"\left", r"\right"):
            i += 1
        else:
            width += 1
            i += 1
    return width


def _env_end(tokens: list[str], i: int) -> int:
    r"""tokens[i] == \begin; return the index of the matching \end."""
    depth = 0
    for j in range(i, len(tokens)):
        if tokens[j] == r"\begin":
            depth += 1
        elif tokens[j] == r"\end":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError(r"unbalanced \begin/\end")


def _split_rows(tokens: list[str]) -> list[list[str]]:
    rows: list[list[str]] = [[]]
    depth = 0
    for tok in tokens:
        depth += {"{": 1, "}": -1, r"\begin": 1, r"\end": -1}.get(tok, 0)
        if tok == r"\\" and depth == 0:
            rows.append([])
        else:
            rows[-1].append(tok)
    return rows


def _segments(tokens: list[str]) -> tuple[list[list[str]], bool]:
    r"""Split at depth-0 break operators (each operator starts a segment). Returns (segments, blocked).

    blocked = the equation has \left..\right or an environment at depth 0, inside which no split is made.
    """
    segments: list[list[str]] = [[]]
    depth = left = 0
    blocked = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == r"\begin":
            end = command_arg(tokens, _env_end(tokens, i))[1]
            segments[-1].extend(tokens[i : end + 1])
            blocked = True
            i = end + 1
            continue
        depth += {"{": 1, "}": -1}.get(tok, 0)
        left += {r"\left": 1, r"\right": -1}.get(tok, 0)
        blocked |= tok == r"\left"
        prev = next((t for t in reversed(segments[-1]) if not is_space(t)), None)
        # a sign right after another operator or at the start is unary, not a break point
        unary = tok in ("+", "-") and (prev is None or prev in _BREAKS or prev in ("^", "_"))
        if depth == 0 and left == 0 and tok in _BREAKS and not unary and any(not is_space(t) for t in segments[-1]):
            segments.append([])
        segments[-1].append(tok)
        i += 1
    return segments, blocked


def wrap_equation(latex: str, width: int) -> tuple[str, list[str]]:
    r"""Break into \begin{aligned} at depth-0 relations/operators when the estimated width exceeds `width`."""
    if width <= 0:
        return latex, []
    tokens = tokenize(latex)
    if estimate_width(tokens) <= width:
        return latex, []
    if any(t in ("&", r"\\") for t in _depth0(tokens)):
        return latex, [r"wrap-eq: equation already has & or \\ at top level; left unwrapped"]
    segments, blocked = _segments(tokens)
    lines: list[list[list[str]]] = [[]]
    line_width = 0
    for seg in segments:
        w = estimate_width(seg)
        if lines[-1] and line_width + w > width:
            lines.append([])
            line_width = 0
        lines[-1].append(seg)
        line_width += w
    if len(lines) == 1:
        why = r"inside \left..\right or an environment" if blocked else "no top-level operator"
        return latex, [f"wrap-eq: width > {width} but no split point ({why}); left unwrapped"]

    rendered: list[str] = []
    placed = False  # the first relation gets the alignment point: &=
    for k, line in enumerate(lines):
        parts = ["".join(seg) for seg in line]
        rel = next((j for j, seg in enumerate(line) if _head(seg) in _RELATIONS), None)
        if not placed and rel is not None:
            parts[rel] = "&" + parts[rel].lstrip()
            placed = True
            rendered.append("".join(parts).strip())
        elif k == 0:
            rendered.append("&" + "".join(parts).strip())
        else:  # continuation: {} keeps a leading +/- binary
            rendered.append(("&" if _head(line[0]) in _RELATIONS else "&{}") + "".join(parts).strip())
    return r"\begin{aligned}" + r"\\".join(rendered) + r"\end{aligned}", []


def _depth0(tokens: list[str]):
    depth = 0
    for tok in tokens:
        depth += {"{": 1, "}": -1, r"\begin": 1, r"\end": -1}.get(tok, 0)
        if depth == 0:
            yield tok


def _head(seg: list[str]) -> str | None:
    return next((t for t in seg if not is_space(t)), None)
