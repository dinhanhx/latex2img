import pytest

from latex2img.labels import canonicalize


@pytest.mark.parametrize(
    "src,expected",
    [
        ("x^2 + {x}+{y}", "x^{2}+x+y"),
        (r"a \le b \ge c \ne d \to e", r"a\leq b\geq c\neq d\rightarrow e"),
        (r"\frac{a}{b}", r"\frac{a}{b}"),
        ("{a+b}^2", "{a+b}^{2}"),
        (r"\text{a  b}", r"\text{a  b}"),
        (r"{}+ c", "{}+c"),
        (r"\sqrt[3]{x}", r"\sqrt[3]{x}"),
        (r"x_\alpha", r"x_{\alpha}"),
        (r"\alpha b", r"\alpha b"),
    ],
)
def test_canonicalize(src, expected):
    assert canonicalize(src) == expected


def test_custom_synonyms():
    assert canonicalize(r"a \le b", {r"\le": r"\leqslant"}) == r"a\leqslant b"
