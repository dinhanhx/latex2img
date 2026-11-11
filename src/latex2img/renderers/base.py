from __future__ import annotations

from typing import Protocol, runtime_checkable

from latex2img.models import OutputFormat, RenderJob, RenderResult


class BackendUnavailable(RuntimeError):
    """Backend cannot start (no Chromium, missing assets). CLI maps this to exit 3."""


@runtime_checkable
class Renderer(Protocol):
    name: str
    supported_formats: frozenset[OutputFormat]

    async def __aenter__(self) -> Renderer: ...  # start browser / check binary

    async def __aexit__(self, *exc: object) -> None: ...

    async def render(self, job: RenderJob) -> RenderResult: ...


def get_renderer(name: str, **kwargs: object) -> Renderer:
    if name == "mathjax":
        from latex2img.renderers.mathjax import MathJaxRenderer  # noqa: PLC0415  (mathjax imports base)

        return MathJaxRenderer(**kwargs)
    raise ValueError(f"backend {name!r} is not available in v1 (only 'mathjax')")
