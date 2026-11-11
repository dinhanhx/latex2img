import json

from typer.testing import CliRunner

from latex2img.cli import app

runner = CliRunner()


def test_usage_errors(tmp_path):
    assert runner.invoke(app, ["render", "x", "-f", "pdf", "-o", str(tmp_path / "a.pdf")]).exit_code == 2
    assert runner.invoke(app, ["render", "x", "--backend", "tectonic"]).exit_code == 2
    dup = tmp_path / "dup.jsonl"
    dup.write_text('{"id": "a", "latex": "x"}\n{"id": "a", "latex": "y"}\n')
    assert runner.invoke(app, ["batch", str(dup), "-o", str(tmp_path / "o")]).exit_code == 2


def test_render_png(tmp_path):
    out = tmp_path / "e.png"
    res = runner.invoke(app, ["render", "$E = mc^2$", "-o", str(out)])
    assert res.exit_code == 0, res.output
    assert res.stdout.strip() == str(out) and out.read_bytes().startswith(b"\x89PNG")


def test_render_stdin_svg(tmp_path):
    out = tmp_path / "e.svg"
    res = runner.invoke(app, ["render", "-", "-f", "svg", "-o", str(out)], input="E = mc^2\n")
    assert res.exit_code == 0 and b"<svg" in out.read_bytes()


def test_render_failure_exit_1(tmp_path):
    assert runner.invoke(app, ["render", r"\frac{", "-o", str(tmp_path / "x.png")]).exit_code == 1


def test_batch_manifest_variants_and_resume(tmp_path):
    src = tmp_path / "eqs.txt"
    src.write_text("# comment\nE = mc^2\n\n\\text{giá đất nông nghiệp} = x\n\\frac{\n")
    out = tmp_path / "out"
    args = ["batch", str(src), "-o", str(out), "--variants", "2", "--seed", "7", "--workers", "2",
            "--color-mode", "random", "--scale-range", "1,2", "--wrap-text-range", "0,8",
            "--wrap-valign", "random", "--label-files"]  # fmt: skip
    res = runner.invoke(app, args)
    assert res.exit_code == 1  # one bad equation, continue-on-error
    rows = {r["id"]: r for r in map(json.loads, (out / "manifest.jsonl").read_text().splitlines())}
    assert set(rows) == {"000002_00", "000002_01", "000004_00", "000004_01", "000005_00", "000005_01"}
    assert rows["000005_00"]["error"] and rows["000005_00"]["image"] is None
    good = rows["000004_01"]
    assert (out / good["image"]).exists() and (out / "labels" / "000004_01.tex").exists()
    assert good["label"] == good["latex_rendered"] and good["params"]["bg"]
    # second run: same params (seeded), images skipped, manifest rebuilt
    res2 = runner.invoke(app, args)
    rows2 = {r["id"]: r for r in map(json.loads, (out / "manifest.jsonl").read_text().splitlines())}
    assert rows2["000004_01"]["params"] == good["params"] and rows2["000004_01"]["width"] == good["width"]
    assert res2.exit_code == 1


def test_batch_manifest_stdout_and_jsonl_overrides(tmp_path):
    src = tmp_path / "eqs.jsonl"
    src.write_text('{"id": "a", "latex": "\\\\text{one two three}", "wrap_text": 3, "format": "svg"}\n')
    res = runner.invoke(app, ["batch", str(src), "-o", str(tmp_path / "o"), "--manifest", "-"])
    assert res.exit_code == 0, res.output
    row = json.loads(res.stdout)
    assert row["image"] == "images/a.svg" and r"\begin{matrix}" in row["latex_rendered"]
    # CLI flag beats the JSONL field
    res = runner.invoke(app, ["batch", str(src), "-o", str(tmp_path / "o2"), "--manifest", "-", "--wrap-text", "0"])
    assert r"\begin{matrix}" not in json.loads(res.stdout)["latex_rendered"]
