"""MathJax 4.1 in headless Chromium via Playwright. One browser; pages pooled per (math font, scale)."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
from collections import defaultdict
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, Route, async_playwright
from playwright.async_api import Error as PlaywrightError

from latex2img.models import OutputFormat, RenderJob, RenderResult
from latex2img.renderers.base import BackendUnavailable

log = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ORIGIN = "http://latex2img.local"  # served by page.route from local files, never the network
DEFAULT_FONT = ASSETS / "fonts" / "NotoSerif-Regular.ttf"


def check_assets(math_fonts: list[str], extensions: list[str]) -> list[str]:
    """Missing vendored files, as messages (empty = OK)."""
    need = [ASSETS / "page.html", ASSETS / "mathjax" / "startup.js", DEFAULT_FONT]
    need += [ASSETS / "@mathjax" / f"{f}-font" / "svg.js" for f in math_fonts]
    need += [ASSETS / "mathjax" / "input" / "tex" / "extensions" / f"{e}.js" for e in extensions]
    return [f"missing asset: {p.relative_to(ASSETS.parent)}" for p in need if not p.exists()]


class MathJaxRenderer:
    name = "mathjax"
    supported_formats = frozenset({OutputFormat.PNG, OutputFormat.SVG})

    def __init__(
        self,
        workers: int = 1,
        math_fonts: list[str] | None = None,
        extensions: list[str] | None = None,
        macros: dict[str, object] | None = None,
    ) -> None:
        self.workers = max(1, workers)
        self.math_fonts = list(math_fonts or ["mathjax-newcm"])
        self.extensions = list(extensions or [])
        self.macros = dict(macros or {})
        self.max_pages = max(4, 2 * self.workers)
        self._sem = asyncio.Semaphore(self.workers)
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: dict[float, BrowserContext] = {}
        self._idle: dict[tuple[str, float], list[Page]] = defaultdict(list)
        self._npages = 0
        self._fonts: dict[str, Path] = {}  # url key -> file
        self._lock = asyncio.Lock()
        self._restarts = 0

    async def __aenter__(self) -> MathJaxRenderer:
        missing = check_assets(self.math_fonts, self.extensions)
        if missing:
            raise BackendUnavailable("; ".join(missing) + " (run: pixi run -e vendor vendor-mathjax)")
        await self._start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stop()

    async def _start(self) -> None:
        try:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch()
        except PlaywrightError as e:
            await self._stop()
            raise BackendUnavailable(
                f"cannot launch Chromium: {e.message.splitlines()[0]} (run: pixi run install-browser)"
            )

    async def _stop(self) -> None:
        self._contexts.clear()
        self._idle.clear()
        self._npages = 0
        if self._browser is not None:
            try:
                await self._browser.close()
            except PlaywrightError:
                pass
            self._browser = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None

    # ------------------------------------------------------------- page pool

    async def _route(self, route: Route) -> None:
        path = route.request.url[len(ORIGIN) :].split("?")[0].lstrip("/")
        if path.startswith("font/"):
            file = self._fonts.get(path[5:])
        else:
            file = (ASSETS / path).resolve()
            if not file.is_relative_to(ASSETS):
                file = None
        if file is None or not file.is_file():
            await route.fulfill(status=404)
            return
        ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        await route.fulfill(status=200, body=file.read_bytes(), content_type=ctype)

    async def _context(self, scale: float) -> BrowserContext:
        if scale not in self._contexts:
            ctx = await self._browser.new_context(device_scale_factor=scale, viewport={"width": 1280, "height": 720})
            await ctx.route(f"{ORIGIN}/**", self._route)
            # block everything else so a missing vendored file can never fall back to a CDN
            await ctx.route(lambda url: not url.startswith(ORIGIN), lambda route: route.abort())
            self._contexts[scale] = ctx
        return self._contexts[scale]

    async def _acquire(self, math_font: str, scale: float) -> Page:
        async with self._lock:
            idle = self._idle[(math_font, scale)]
            if idle:
                return idle.pop()
            if self._npages >= self.max_pages:  # evict an idle page of another key
                for pages in self._idle.values():
                    if pages:
                        await pages.pop(0).close()
                        self._npages -= 1
                        break
            ctx = await self._context(scale)
            self._npages += 1
        try:
            page = await ctx.new_page()
            cfg = {"font": math_font, "extensions": self.extensions, "macros": self.macros}
            await page.add_init_script(f"window.L2I = {json.dumps(cfg)};")
            await page.goto(f"{ORIGIN}/page.html")
            await page.wait_for_function("window.L2I_READY === true || !!window.L2I_ERROR", timeout=30_000)
            error = await page.evaluate("window.L2I_ERROR || null")
            if error:
                await page.close()
                raise PlaywrightError(f"MathJax failed to load: {error}")
            return page
        except BaseException:
            self._npages -= 1
            raise

    async def _discard(self, page: Page) -> None:
        self._npages -= 1
        try:
            await page.close()
        except PlaywrightError:
            pass

    # ------------------------------------------------------------- rendering

    async def render(self, job: RenderJob) -> RenderResult:
        if job.fmt not in self.supported_formats:
            return RenderResult(job.id, None, job.fmt, error=f"format {job.fmt.value} not supported by mathjax")
        if job.math_font not in self.math_fonts:
            return RenderResult(job.id, None, job.fmt, error=f"math font {job.math_font} not loaded")
        async with self._sem:
            for attempt in range(2):
                page = None
                try:
                    page = await self._acquire(job.math_font, job.scale)
                    result = await asyncio.wait_for(self._render_on_page(page, job), job.timeout_s)
                    self._idle[(job.math_font, job.scale)].append(page)
                    return result
                except asyncio.TimeoutError:
                    if page is not None:
                        await self._discard(page)  # page may be stuck mid-render
                    return RenderResult(job.id, None, job.fmt, error=f"timeout after {job.timeout_s}s", timed_out=True)
                except PlaywrightError as e:
                    if page is not None:
                        await self._discard(page)
                    if attempt == 0 and await self._restart_if_crashed():
                        continue
                    return RenderResult(job.id, None, job.fmt, error=f"browser error: {e.message.splitlines()[0]}")
        raise AssertionError("unreachable")

    async def _restart_if_crashed(self) -> bool:
        """Browser crash -> restart once per renderer lifetime, so in-flight jobs retry."""
        async with self._lock:
            if self._browser is not None and self._browser.is_connected():
                return True  # someone else already restarted, or the page alone failed: retry
            if self._restarts >= 1:
                return False
            self._restarts += 1
            log.warning("Chromium crashed; restarting once")
            await self._stop()
            await self._start()
            return True

    async def _render_on_page(self, page: Page, job: RenderJob) -> RenderResult:
        font = job.font or DEFAULT_FONT
        key = str(abs(hash(str(font))))
        self._fonts[key] = Path(font)
        family = f"L2I_{key}"
        await page.evaluate("([f, u]) => l2iSetFont(f, u)", [family, f"{ORIGIN}/font/{key}"])
        out = await page.evaluate(
            "(args) => l2iRender(args)",
            {"tex": job.latex, "display": job.display, "family": family, "color": job.color},
        )
        if "error" in out:
            return RenderResult(job.id, None, job.fmt, error=out["error"])
        if job.fmt is OutputFormat.SVG:
            return RenderResult(job.id, out["svg"].encode(), job.fmt)
        png = await page.locator("#host svg").first.screenshot(omit_background=True)
        return RenderResult(job.id, png, job.fmt)
