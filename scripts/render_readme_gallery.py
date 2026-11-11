"""Render the README gallery: the five themes as a paper shows them.

A small paper with papermint is compiled, its five figures are drawn through
``Document``, and each figure is rendered to a PNG. The checkouts of macromint
and papermint must sit next to this repository, and pdftoppm must be installed.
"""

import shutil
import subprocess  # noqa: S404  # pdflatex and pdftoppm on files this script wrote
import tempfile
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from figmint import Document, legend

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "scripts" / "gallery" / "main.tex"
# The packages the paper loads, copied beside it as a paper vendors them.
PACKAGES = (
    REPO / "tex" / "latex" / "figmint" / "figmint.sty",
    REPO.parent / "macromint" / "tex" / "latex" / "macromint" / "macromint.sty",
    REPO.parent / "papermint" / "tex" / "latex" / "papermint" / "papermint.sty",
)
THEMES = ("normal", "latte", "frappe", "macchiato", "mocha")
LABELS = ("baseline", "variant A", "variant B", "variant C")
RATES = (0.045, 0.075, 0.12, 0.19)
STEPS = np.linspace(0.0, 80.0, 161)
DPI = 300


def draw_curves(figure: Figure, axes: Axes) -> None:  # noqa: ARG001
    """Draw four decaying curves on a log axis with a legend."""
    for label, rate in zip(LABELS, RATES, strict=True):
        axes.plot(STEPS, 0.018 + 0.982 * np.exp(-rate * STEPS), label=label)

    axes.set_xlim(0.0, 80.0)
    axes.set_ylim(1.0e-2, 1.2)
    axes.set_yscale("log")
    axes.set_xlabel(r"Step $t$")
    axes.set_ylabel("Relative value")
    legend(axes, loc="best")


def run(command: list[str], directory: Path) -> None:
    """Run a command in a directory.

    Raises:
        RuntimeError: If the command fails.
    """
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        msg = f"{command[0]} failed:\n{completed.stdout[-3000:]}"
        raise RuntimeError(msg)


def render_gallery(output_dir: Path) -> None:
    """Render the gallery PNGs into a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)

        for package in PACKAGES:
            shutil.copy(package, directory)

        source = Path(shutil.copy(PAPER, directory))
        run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", source.name],
            directory,
        )
        document = Document(
            source.with_suffix(".figmint"), results="gallery", repo=REPO
        )

        for theme in THEMES:
            document.figure(f"theme_{theme}")(draw_curves)

        document.main(["--all"])

        for theme in THEMES:
            pdf = directory / "figures" / f"theme_{theme}.pdf"
            target = output_dir / f"theme_{theme}"
            run(
                [
                    "pdftoppm",
                    "-png",
                    "-r",
                    str(DPI),
                    "-singlefile",
                    str(pdf),
                    str(target),
                ],
                directory,
            )


def main() -> None:
    """Render the gallery from the command line."""
    render_gallery(REPO / "gallery")


if __name__ == "__main__":
    main()
