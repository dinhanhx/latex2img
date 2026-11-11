"""Brace-aware LaTeX tokenizer. Tokens are plain strings; groups are found by brace matching."""

from __future__ import annotations

import regex

# control word | control symbol (\\, \{, \ , ...) | comment | whitespace run | one grapheme
_TOKEN = regex.compile(r"\\[a-zA-Z]+|\\.|%[^\n]*|\s+|\X", regex.S)
_GRAPHEME = regex.compile(r"\X")

# commands whose single brace argument is text mode (content is not math)
TEXT_COMMANDS = frozenset({r"\text", r"\textrm", r"\textbf", r"\textit", r"\textsf", r"\texttt", r"\mbox", r"\ml"})


def tokenize(s: str) -> list[str]:
    return _TOKEN.findall(s)


def is_space(tok: str) -> bool:
    return tok.isspace()


def is_control_word(tok: str) -> bool:
    return len(tok) > 1 and tok[0] == "\\" and tok[1].isalpha()


def graphemes(s: str) -> int:
    return len(_GRAPHEME.findall(s))


def skip_space(tokens: list[str], i: int) -> int:
    while i < len(tokens) and (is_space(tokens[i]) or tokens[i].startswith("%")):
        i += 1
    return i


def group_end(tokens: list[str], i: int) -> int:
    """tokens[i] == '{'; return index of the matching '}'. Raises ValueError if unbalanced."""
    depth = 0
    for j in range(i, len(tokens)):
        if tokens[j] == "{":
            depth += 1
        elif tokens[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("unbalanced braces")


def command_arg(tokens: list[str], i: int) -> tuple[int, int] | None:
    """For a command at tokens[i], return (open, close) indices of its brace argument, if any."""
    j = skip_space(tokens, i + 1)
    if j < len(tokens) and tokens[j] == "{":
        return j, group_end(tokens, j)
    return None
