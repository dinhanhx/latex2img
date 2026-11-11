"""Golden images. Regenerate with UPDATE_GOLDEN=1 pytest tests/test_golden.py"""

import io
import os
from pathlib import Path

import pytest
from conftest import MATH_FONTS, render_many
from PIL import Image, ImageChops, ImageStat

from latex2img.fonts import font_for_lang, resolve_font
from latex2img.models import RenderJob
from latex2img.postprocess import finish_png
from latex2img.preprocess import expand_ml, normalize, wrap_text

GOLDEN = Path(__file__).parent / "golden"
VI = [
    r"P = \text{giá đất nông nghiệp} \times S",
    r"\text{ệ ổ ừ ặ ỡ ữ ậ ẫ}",
    r"\text{Nguyễn Thị Hướng} + \text{Phường Đống Đa}",
    r"T = \text{thuế suất} \cdot \text{diện tích}",
    r"\frac{\text{tổng thu nhập}}{\text{số người}}",
    r"x_{\text{tối đa}}^{\text{tối thiểu}}",
    r"giá đất = \text{đơn giá} \times k",
]
EN = [
    "E = mc^2",
    r"\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}",
    r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}",
    r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}",
    r"\begin{aligned} a &= b + c \\ &= d \end{aligned}",
    r"\left( \frac{a}{b} \right)^2",
    r"\text{price of agricultural land} = \text{tax} \times \text{dollars per square meter}",
    r"\ml{price of \\ agricultural land} = x",
    r"\begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}",
    r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
    r"f(x) = \begin{cases} 1 & x > 0 \\ 0 & \text{otherwise} \end{cases}",
    r"\mathbb{R}^n \subseteq \mathcal{F}",
    r"\overbrace{a + b}^{n} \cdot \underline{c}",
    r"\sqrt[3]{x^3 + y^3}",
]
CJK = [("zh", r"\text{面积} = a \cdot b"), ("ja", r"\text{速度} = \frac{d}{t}"), ("ko", r"\text{넓이} = l \times w")]
CASES = (
    [("vi", s, "mathjax-newcm") for s in VI]
    + [("en", s, "mathjax-newcm") for s in EN]
    + [(lang, s, "mathjax-newcm") for lang, s in CJK]
    + [("en", r"\frac{a+b}{c} = \sqrt{x^2}", f) for f in MATH_FONTS]
)


def _jobs():
    jobs = []
    for i, (lang, latex, mf) in enumerate(CASES):
        try:
            font = resolve_font(font_for_lang(lang))
        except FileNotFoundError:
            continue  # CJK system font missing on this host
        src = expand_ml(wrap_text(normalize(latex), 12))
        jobs.append(RenderJob(f"g{i:02d}", src, lang=lang, font=font, math_font=mf))
    return jobs


def test_golden_images():
    jobs = _jobs()
    results = render_many(jobs, extensions=[])
    update = os.environ.get("UPDATE_GOLDEN") == "1"
    GOLDEN.mkdir(exist_ok=True)
    for job, res in zip(jobs, results):
        assert res.ok, f"{job.id}: {res.error}"
        png, _, _ = finish_png(res.data, "#ffffff", 4)
        path = GOLDEN / f"{job.id}.png"
        if update or not path.exists():
            path.write_bytes(png)
            continue
        got, want = Image.open(io.BytesIO(png)).convert("L"), Image.open(path).convert("L")
        assert abs(got.width - want.width) <= 2 and abs(got.height - want.height) <= 2, job.id
        if got.size != want.size:
            got = got.resize(want.size)
        diff = ImageStat.Stat(ImageChops.difference(got, want)).mean[0]
        assert diff < 8, f"{job.id}: mean abs diff {diff:.1f}"


@pytest.mark.parametrize("valign", ["t"])
def test_array_t_position_supported(valign):
    (res,) = render_many([RenderJob("t", wrap_text(r"\text{a b} = x", 1, valign=valign))])
    assert res.ok
