"""Tests for figure export with provenance."""

import re
import subprocess  # noqa: S404  # the test asks git for the commit the module must record
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from PIL import Image

from figmint import provenance, savefig

REPO = Path(__file__).resolve().parents[1]


def head_commit() -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_pdf_carries_commit_and_results(tmp_path: Path) -> None:
    figure, axis = plt.subplots()
    axis.plot([0.0, 1.0], [0.0, 1.0])
    out = tmp_path / "figure.pdf"

    savefig(figure, out, results="results/run-1", repo=REPO)
    plt.close(figure)

    match = re.search(rb"/Subject \(([^)]*)\)", out.read_bytes())
    assert match is not None
    subject = match.group(1).decode()
    assert subject.startswith("repo=figmint ")
    assert f"commit={head_commit()}" in subject
    assert re.search(r"dirty=(yes|no)", subject) is not None
    assert subject.endswith(" results=results/run-1")


def test_png_carries_the_same_subject(tmp_path: Path) -> None:
    figure, axis = plt.subplots()
    axis.plot([0.0, 1.0], [1.0, 0.0])
    out = tmp_path / "figure.png"

    savefig(figure, out, results="results/run-2", repo=REPO)
    plt.close(figure)

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
