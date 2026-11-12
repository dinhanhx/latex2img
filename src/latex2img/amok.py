"""Random LaTeX formulas for synthetic data: a small grammar, or mutation of an existing corpus."""

from __future__ import annotations

import random

from latex2img.preprocess.tokenizer import TEXT_COMMANDS, command_arg, tokenize

WORDS = {
    "en": "Interest Principal Rate Capital Assets Income Expense Loan Deposit Balance Days Share Price Risk "
    "Liquidity Outflows Yield Payment Fee Margin".split(),
    "vi": "Tiền lãi|Dư nợ|Lãi suất|Vốn tự có|Tổng tài sản|Số ngày|Tiền gửi|Nợ xấu|Kỳ hạn|Thu nhập|Chi phí|"
    "Khoản vay|Số dư|Phí|Lợi nhuận".split("|"),
    "zh": "利息 本金 年利率 存期天数 贷款 存款 资本 资产 收入 支出 余额 风险 还款额 不良贷款 准备金".split(),
}
LETTERS = "abcdxyznkmtrPQRSLKAB"
GREEK = r"\alpha \beta \gamma \delta \lambda \mu \sigma \theta \rho \pi \varepsilon \omega".split()
FUNCS = r"\sin \cos \log \ln \exp".split()
BINOPS = ["+", "-", r"\times", r"\cdot"]
RELS = ["=", r"\leq", r"\geq", r"\approx", "<", ">"]
SKIP_ARG = TEXT_COMMANDS | {r"\begin", r"\end", r"\operatorname", r"\mathrm"}


def _words(rng: random.Random, lang: str) -> str:
    pool = WORDS.get(lang, WORDS["en"])
    return " ".join(rng.sample(pool, rng.choice((1, 1, 2))))


def _number(rng: random.Random) -> str:
    kind = rng.random()
    if kind < 0.6:
        return str(rng.randint(1, 365))
    if kind < 0.85:
        return f"{rng.randint(0, 99)}.{rng.randint(1, 99)}"
    return rf"{rng.randint(1, 150)}\%"


def atom(rng: random.Random, lang: str) -> str:
    r = rng.random()
    if r < 0.4:
        return rng.choice(LETTERS)
    if r < 0.55:
        return rng.choice(GREEK)
    if r < 0.75:
        return _number(rng)
    return rf"\text{{{_words(rng, lang)}}}"


def expr(rng: random.Random, d: int, lang: str) -> str:
    if d <= 0 or rng.random() < 0.25:
        return atom(rng, lang)

    def sub() -> str:
        return expr(rng, d - 1, lang)

    rules = [
        lambda: f"{sub()} {rng.choice(BINOPS)} {sub()}",
        lambda: rf"\frac{{{sub()}}}{{{sub()}}}",
        lambda: rf"\sqrt{{{sub()}}}",
        lambda: f"{atom(rng, lang)}^{{{sub()}}}",
        lambda: f"{atom(rng, lang)}_{{{sub()}}}",
        lambda: rf"\left({sub()}\right)",
        lambda: rf"{rng.choice(FUNCS)}\left({sub()}\right)",
        lambda: rf"\sum_{{i=1}}^{{n}} {sub()}",
        lambda: rf"\int_{{0}}^{{T}} {sub()} \, dt",
    ]
    return rng.choices(rules, weights=[4, 3, 1, 2, 1, 1, 1, 1, 1])[0]()


def generate(rng: random.Random, lang: str = "en", depth: int = 3) -> str:
    lhs = rf"\text{{{_words(rng, lang)}}}" if rng.random() < 0.5 else atom(rng, lang)
    return f"{lhs} {rng.choice(RELS)} {expr(rng, depth, lang)}"


def mutate(rng: random.Random, latex: str, lang: str = "en") -> str:
    """Remap letters consistently, randomize digits/binops, replace \\text{} words; structure and braces are kept."""
    tokens = tokenize(latex)
    letters: dict[str, str] = {}
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in SKIP_ARG and (arg := command_arg(tokens, i)):
            o, c = arg
            inner = _words(rng, lang) if tok in TEXT_COMMANDS else "".join(tokens[o + 1 : c])
            out += [*tokens[i:o], "{", inner, "}"]
            i = c + 1
            continue
        if len(tok) == 1 and tok.isascii() and tok.isalpha():
            tok = letters.setdefault(tok, rng.choice(LETTERS))
        elif tok.isascii() and tok.isdigit():
            tok = rng.choice("123456789")
        elif tok in BINOPS:
            tok = rng.choice(BINOPS) + " "  # "\\times" must not glue onto a following letter
        out.append(tok)
        i += 1
    return "".join(out)
