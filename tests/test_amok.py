from conftest import render_many
from typer.testing import CliRunner

from latex2img.amok import generate, mutate
from latex2img.cli import app
from latex2img.models import RenderJob
from latex2img.preprocess.tokenizer import command_arg, tokenize
from latex2img.randomize import sample_rng

CORPUS = r"\text{CAR} = \frac{\text{Tier 1} + T_{2}}{\text{RWA} + 12.5 \times (K_{m} + K_{o})} \geq 8\%"


def _check(eq: str) -> None:
    assert "\n" not in eq and eq.count("{") == eq.count("}")
    tokens = tokenize(eq)
    for i, tok in enumerate(tokens):
        if tok == r"\text":
            o, c = command_arg(tokens, i)  # raises on unbalanced
            assert c > o + 1


def test_generate_deterministic_and_valid():
    a = [generate(sample_rng(1, "amok", k), "vi") for k in range(200)]
    assert a == [generate(sample_rng(1, "amok", k), "vi") for k in range(200)]
    assert a != [generate(sample_rng(2, "amok", k), "vi") for k in range(200)]
    for eq in a:
        _check(eq)


def test_mutate_keeps_structure():
    for k in range(50):
        eq = mutate(sample_rng(0, "m", k), CORPUS, "zh")
        _check(eq)
        ctrl = [t for t in tokenize(eq) if t.startswith("\\") and t not in (r"\times", r"\cdot")]
        assert not any(t.startswith((r"\times", r"\cdot")) and t not in (r"\times", r"\cdot") for t in tokenize(eq))
        assert ctrl == [t for t in tokenize(CORPUS) if t.startswith("\\") and t not in (r"\times", r"\cdot")]


def test_cli(tmp_path):
    runner = CliRunner()
    res = runner.invoke(app, ["amok", "5", "--seed", "1"])
    assert res.exit_code == 0 and len(res.stdout.splitlines()) == 5
    assert runner.invoke(app, ["amok", "0"]).exit_code == 2
    src = tmp_path / "c.txt"
    src.write_text(CORPUS + "\n")
    out = tmp_path / "r.txt"
    assert runner.invoke(app, ["amok", "3", "--from", str(src), "-o", str(out)]).exit_code == 0
    assert len(out.read_text().splitlines()) == 3


def test_mathjax_accepts_generated():
    eqs = [generate(sample_rng(3, "amok", k), lang, 4) for k, lang in enumerate(["en", "vi", "zh"] * 10)]
    eqs += [mutate(sample_rng(3, "m", k), c) for k in range(10) for c in (CORPUS, "(1+c)^{n}")]
    results = render_many([RenderJob(str(k), eq) for k, eq in enumerate(eqs)])
    assert all(r.ok for r in results), [(eq, r.error) for eq, r in zip(eqs, results) if not r.ok]
