"""Delimiter stripping, NFC normalization, auto-text."""

from __future__ import annotations

import unicodedata

import regex

from latex2img.preprocess.tokenizer import command_arg, is_space, tokenize

_DELIMS = [("$$", "$$"), (r"\[", r"\]"), (r"\(", r"\)"), ("$", "$")]
# arguments of these are left alone by auto-text
_SKIP_COMMANDS = frozenset(
    {r"\text", r"\mathrm", r"\operatorname", r"\ml", r"\textrm", r"\textbf", r"\textit", r"\mbox"}
)
_LETTER = regex.compile(r"^\p{L}\p{M}*$")
_ASCII = regex.compile(r"^[A-Za-z]$")


def strip_delimiters(s: str) -> str:
    s = s.strip()
    for left, right in _DELIMS:
        if len(s) >= len(left) + len(right) and s.startswith(left) and s.endswith(right):
            return s[len(left) : len(s) - len(right)].strip()
    return s


def auto_text(latex: str) -> str:
    r"""Wrap bare words containing non-ASCII letters into \text{}.

    A word is a run of letters (ASCII included, so `nông` stays one word); consecutive such words separated
    only by whitespace become one \text{} with single spaces, since math mode would drop the spaces.
    """
    tokens = tokenize(latex)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _SKIP_COMMANDS:
            arg = command_arg(tokens, i)
            end = arg[1] if arg else i
            out.extend(tokens[i : end + 1])
            i = end + 1
            continue
        if tok.startswith("\\") and len(tok) > 1 and tok[1].isalpha():
            out.append(tok)
            i += 1
            continue
        word_end = _word_end(tokens, i)
        if word_end > i and _has_non_ascii(tokens[i:word_end]):
            words = ["".join(tokens[i:word_end])]
            i = word_end
            while True:  # absorb following non-ASCII words separated by whitespace
                j = i
                while j < len(tokens) and is_space(tokens[j]):
                    j += 1
                k = _word_end(tokens, j)
                if j == i or k == j or not _has_non_ascii(tokens[j:k]):
                    break
                words.append("".join(tokens[j:k]))
                i = k
            out.append(r"\text{" + " ".join(words) + "}")
            continue
        out.append(tok)
        i += 1
    return "".join(out)


def _word_end(tokens: list[str], i: int) -> int:
    while i < len(tokens) and _LETTER.match(tokens[i]):
        i += 1
    return i


def _has_non_ascii(tokens: list[str]) -> bool:
    return any(not _ASCII.match(t) for t in tokens)


def normalize(latex: str, auto: bool = True) -> str:
    s = unicodedata.normalize("NFC", strip_delimiters(latex))
    return auto_text(s) if auto else s
