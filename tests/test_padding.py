import io
import json

from PIL import Image
from typer.testing import CliRunner

from latex2img.cli import app
from latex2img.postprocess import finish_png

runner = CliRunner()


def _png(size, box):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.paste((0, 0, 0, 255), box)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_finish_png_trims_then_pads():
    data, w, h = finish_png(_png((50, 40), (10, 5, 20, 25)), "#ffffff", 7)
    assert (w, h) == (10 + 14, 20 + 14)
    img = Image.open(io.BytesIO(data))
    assert img.mode == "RGB" and img.getpixel((6, 6)) == (255, 255, 255) and img.getpixel((7, 7)) == (0, 0, 0)


def test_finish_png_zero_padding_transparent():
    data, w, h = finish_png(_png((50, 40), (10, 5, 20, 25)), None, 0)
    assert (w, h) == (10, 20) and Image.open(io.BytesIO(data)).mode == "RGBA"


def _border(path):
    """Width of the uniform background border on the left edge."""
    img = Image.open(path).convert("RGB")
    bg = img.getpixel((0, 0))
    return next(x for x in range(img.width) if any(img.getpixel((x, y)) != bg for y in range(img.height)))


def test_cli_padding_fixed(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    for out, pad in ((a, "0"), (b, "20")):
        assert runner.invoke(app, ["render", "x+1", "--bg", "white", "--padding", pad, "-o", str(out)]).exit_code == 0
    wa, ha = Image.open(a).size
    assert Image.open(b).size == (wa + 40, ha + 40)
    assert _border(b) == 20


def test_cli_padding_negative_is_usage_error(tmp_path):
    assert runner.invoke(app, ["render", "x", "--padding", "-1", "-o", str(tmp_path / "x.png")]).exit_code == 2
    src = tmp_path / "e.txt"
    src.write_text("x\n")
    res = runner.invoke(app, ["batch", str(src), "-o", str(tmp_path / "o"), "--padding-range", "-2,3"])
    assert res.exit_code == 2


def test_cli_padding_range_sampled_per_variant(tmp_path):
    src = tmp_path / "e.txt"
    src.write_text("x+1\n")
    out = tmp_path / "out"
    args = ["batch", str(src), "-o", str(out), "--variants", "6", "--seed", "3", "--padding-range", "0,30"]
    assert runner.invoke(app, args).exit_code == 0
    rows = [json.loads(line) for line in (out / "manifest.jsonl").read_text().splitlines()]
    pads = [r["params"]["padding"] for r in rows]
    assert all(0 <= p <= 30 for p in pads) and len(set(pads)) > 1
    for r in rows:  # training mode composites a white bg, so the border is measurable
        assert _border(out / r["image"]) == r["params"]["padding"]
