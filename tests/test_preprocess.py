import unicodedata

import pytest

from latex2img.preprocess import expand_ml, normalize, wrap_equation, wrap_text
from latex2img.preprocess.normalize import strip_delimiters
from latex2img.preprocess.tokenizer import group_end, tokenize
from latex2img.preprocess.wrap import estimate_width, word_wrap

SPEC_IN = r"\text{price of agricultural land} = \text{tax} \times \text{dollars per square meter}"
SPEC_OUT = (
    r"\begin{matrix}\text{price of}\\\text{agricultural}\\\text{land}\end{matrix} = \text{tax} \times "
    r"\begin{matrix}\text{dollars per}\\\text{square meter}\end{matrix}"
)


def test_tokenizer_escaped_braces_are_not_groups():
    toks = tokenize(r"\{a\} {b}")
    assert toks[:3] == [r"\{", "a", r"\}"]
    assert group_end(toks, toks.index("{")) == toks.index("}")


def test_tokenizer_unbalanced():
    with pytest.raises(ValueError):
        group_end(tokenize(r"\frac{"), 1)


@pytest.mark.parametrize("src", ["$x$", "$$x$$", r"\[x\]", r"\(x\)", "  x "])
def test_strip_delimiters(src):
    assert strip_delimiters(src) == "x"


def test_nfd_vietnamese_is_nfc():
    nfd = unicodedata.normalize("NFD", r"\text{nghiệp}")
    assert normalize(nfd) == r"\text{nghiệp}"


def test_auto_text_joins_words_and_keeps_ascii_math():
    assert normalize(r"P = giá đất nông nghiệp \times S") == r"P = \text{giá đất nông nghiệp} \times S"
    assert normalize("x + y") == "x + y"
    assert normalize(r"\mathrm{đất} + \operatorname{giá}") == r"\mathrm{đất} + \operatorname{giá}"
    assert normalize("x_{ệ}") == r"x_{\text{ệ}}"
    assert normalize("giá", auto=False) == "giá"


def test_wrap_text_spec_example():
    assert wrap_text(SPEC_IN, 12) == SPEC_OUT


def test_wrap_text_align_and_valign():
    out = wrap_text(r"\text{a b}", 1, align="l")
    assert out == r"\begin{array}{l}\text{a}\\\text{b}\end{array}"
    assert wrap_text(r"\text{a b}", 1, valign="t") == r"\begin{array}[t]{c}\text{a}\\\text{b}\end{array}"


def test_wrap_text_widths():
    assert wrap_text(SPEC_IN, 0) == SPEC_IN
    assert word_wrap("supercalifragilistic is long", 5) == ["supercalifragilistic", "is", "long"]
    # grapheme count, not code points: "ệ" in NFD is 3 code points but 1 grapheme
    assert word_wrap(unicodedata.normalize("NFD", "ệệ ệệ"), 5) == [unicodedata.normalize("NFD", "ệệ ệệ")]


def test_wrap_text_nested_in_frac_and_scripts():
    out = wrap_text(r"\frac{\text{a b}}{x}^{\text{c d}}", 1)
    assert out == (
        r"\frac{\begin{matrix}\text{a}\\\text{b}\end{matrix}}{x}^{\begin{matrix}\text{c}\\\text{d}\end{matrix}}"
    )


def test_ml_expansion_skips_width_wrapping():
    src = r"\ml{price of \\ agricultural land} = x"
    assert wrap_text(src, 3) == src
    out = r"\begin{matrix}\text{price of}\\\text{agricultural land}\end{matrix} = x"
    assert expand_ml(wrap_text(src, 3)) == out


def test_estimate_width():
    assert estimate_width(tokenize(r"\text{abc} + \frac{ab}{abcd}")) == 3 + 1 + 4


def test_wrap_equation_splits_at_operators():
    out, warns = wrap_equation("E = a + b + c + d", 5)
    assert not warns
    assert out == r"\begin{aligned}E &= a + b\\&{}+ c + d\end{aligned}"
    assert wrap_equation("E = a", 5) == ("E = a", [])


def test_wrap_equation_refused_inside_left_right():
    src = r"\left( a + b + c + d \right)"
    out, warns = wrap_equation(src, 3)
    assert out == src and warns


def test_wrap_equation_unary_minus_not_split():
    out, _ = wrap_equation("x = -a - b", 3)
    assert r"&= -a" in out
