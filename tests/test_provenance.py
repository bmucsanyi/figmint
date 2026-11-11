"""Tests for figure export with provenance."""

import re
import subprocess  # noqa: S404  # the test asks git for the commit the module must record
from pathlib import Path

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from figmint import provenance, savefig
from figmint._provenance import tex_escape

REPO = Path(__file__).resolve().parents[1]


def head_commit() -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def new_figure() -> Figure:
    figure = Figure()
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    axis.plot([0.0, 1.0], [0.0, 1.0])

    return figure


def test_pdf_carries_commit_and_results(tmp_path: Path) -> None:
    out = tmp_path / "figure.pdf"

    savefig(new_figure(), out, results="results/run-1", repo=REPO)

    match = re.search(rb"/Subject \(([^)]*)\)", out.read_bytes())
    assert match is not None
    subject = match.group(1).decode()
    # The script field names the running script when it is inside the repository,
    # which pytest's own entry point is.
    assert re.fullmatch(
        rf"repo=figmint commit={head_commit()}( script=\S+)? results=results/run-1",
        subject,
    )


def test_png_carries_the_same_subject(tmp_path: Path) -> None:
    out = tmp_path / "figure.png"

    savefig(new_figure(), out, results="results/run-2", repo=REPO)

    with Image.open(out) as image:
        subject = image.info["Subject"]

    assert subject == provenance(results="results/run-2", repo=REPO)["Subject"]


def test_results_are_optional() -> None:
    subject = provenance(repo=REPO)["Subject"]

    assert "results=" not in subject
    assert f"commit={head_commit()}" in subject


def test_outside_a_repository_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="rev-parse"):
        provenance(repo=tmp_path)


def test_tex_escape_covers_the_special_characters() -> None:
    assert tex_escape("a_b%c#d&e$f{g}h~i^j\\k") == (
        r"a\_b\%c\#d\&e\$f\{g\}h\textasciitilde{}i\textasciicircum{}j\textbackslash{}k"
    )
