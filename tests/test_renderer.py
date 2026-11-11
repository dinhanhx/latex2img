import io

from conftest import render_many
from PIL import Image

from latex2img.labels import canonicalize
from latex2img.models import OutputFormat, RenderJob
from latex2img.postprocess import finish_png
from latex2img.renderers.base import Renderer
from latex2img.renderers.mathjax import MathJaxRenderer


def test_protocol():
    assert isinstance(MathJaxRenderer(), Renderer)


def test_contract_ok_and_errors_are_results():
    jobs = [
        RenderJob("ok", "E = mc^2"),
        RenderJob("svg", "x", fmt=OutputFormat.SVG),
        RenderJob("brace", r"\frac{"),
        RenderJob("undef", r"\undefinedmacro"),
        RenderJob("pdf", "x", fmt=OutputFormat.PDF),
    ]
    ok, svg, brace, undef, pdf = render_many(jobs)
    assert ok.ok and ok.data.startswith(b"\x89PNG")
    assert svg.ok and b"<svg" in svg.data
    assert not brace.ok and "brace" in brace.error.lower()
    assert not undef.ok and "undefinedmacro" in undef.error
    assert not pdf.ok


def test_canonical_label_renders_same_png():
    raw = r"x^2 + {a}+{b} \le \frac{1}{2}"
    a, b = render_many([RenderJob("raw", raw), RenderJob("canon", canonicalize(raw))])
    assert a.data and b.data
    ia, ib = (Image.open(io.BytesIO(finish_png(r.data, "#ffffff", 0)[0])) for r in (a, b))
    assert ia.size == ib.size and ia.tobytes() == ib.tobytes()
