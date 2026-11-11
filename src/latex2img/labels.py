"""--label-normalize canonical: token-level rewrites of the label only (never the render source)."""

from __future__ import annotations

from latex2img.preprocess.tokenizer import TEXT_COMMANDS, command_arg, group_end, is_control_word, is_space, tokenize

DEFAULT_SYNONYMS = {r"\le": r"\leq", r"\ge": r"\geq", r"\ne": r"\neq", r"\to": r"\rightarrow"}


def canonicalize(latex: str, synonyms: dict[str, str] | None = None) -> str:
    syn = DEFAULT_SYNONYMS if synonyms is None else synonyms
    return "".join(_join(_canon(tokenize(latex), syn)))


def _canon(tokens: list[str], syn: dict[str, str]) -> list[str]:
    out: list[str] = []
    i = 0
    arg_context = False  # next brace group is a command/script argument -> keep its braces
    while i < len(tokens):
        tok = tokens[i]
        if is_space(tok) or tok.startswith("%"):
            i += 1
            continue
        if tok in TEXT_COMMANDS and (arg := command_arg(tokens, i)):
            out.append(tok)
            out.append("".join(tokens[arg[0] : arg[1] + 1]))  # text-mode content kept verbatim
            i = arg[1] + 1
            arg_context = True
            continue
        if tok in ("^", "_"):
            out.append(tok)
            j = _skip(tokens, i + 1)
            takes_arg = j < len(tokens) and is_control_word(tokens[j]) and command_arg(tokens, j)
            if j < len(tokens) and tokens[j] != "{" and not takes_arg:  # x^2 -> x^{2}
                out.extend(["{", syn.get(tokens[j], tokens[j]), "}"])
                i = j + 1
                arg_context = False
            else:
                i = j
                arg_context = True
            continue
        if tok == "{":
            end = group_end(tokens, i)
            inner = _canon(tokens[i + 1 : end], syn)
            nxt = _skip(tokens, end + 1)
            before_script = nxt < len(tokens) and tokens[nxt] in ("^", "_")
            if arg_context or not inner or _has_switch(inner) or (before_script and len(inner) > 1):
                out.extend(["{", *inner, "}"])
                # a closing arg brace can be followed by another arg: \frac{a}{b}
            else:
                out.extend(inner)
                arg_context = False
            i = end + 1
            continue
        out.append(syn.get(tok, tok) if is_control_word(tok) else tok)
        arg_context = is_control_word(tok) or tok == "]"
        i += 1
    return out


def _has_switch(tokens: list[str]) -> bool:
    # groups scoping \over, font switches, or rows must keep their braces
    return any(is_control_word(t) and t not in TEXT_COMMANDS for t in tokens) or any(t in ("&", r"\\") for t in tokens)


def _skip(tokens: list[str], i: int) -> int:
    while i < len(tokens) and (is_space(tokens[i]) or tokens[i].startswith("%")):
        i += 1
    return i


def _join(tokens: list[str]) -> list[str]:
    """One space only where TeX needs it: after a control word before a letter."""
    out: list[str] = []
    for tok in tokens:
        if out and is_control_word(out[-1]) and tok[:1].isalpha():
            out.append(" ")
        out.append(tok)
    return out
