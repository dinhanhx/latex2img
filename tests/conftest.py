import asyncio

import pytest

from latex2img.renderers.base import BackendUnavailable
from latex2img.renderers.mathjax import MathJaxRenderer

MATH_FONTS = ["mathjax-newcm", "mathjax-stix2", "mathjax-pagella"]


def render_many(jobs, **kwargs):
    """Render jobs with one renderer; skips the test when Chromium/assets are unavailable."""

    async def go():
        async with MathJaxRenderer(workers=4, math_fonts=MATH_FONTS, **kwargs) as r:
            return await asyncio.gather(*(r.render(j) for j in jobs))

    try:
        return asyncio.run(go())
    except BackendUnavailable as e:
        pytest.skip(str(e))
