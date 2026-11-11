"""Compiling the test documents and reading what their PDFs show."""

import os
import re
import shutil
import subprocess  # noqa: S404  # a TeX engine on a test document this module copied
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pdfminer.high_level import extract_pages
from pdfminer.layout import (
    LAParams,
    LTChar,
    LTContainer,
    LTFigure,
    LTPage,
    LTTextLine,
)

from figmint import (
    Document,
    area,
    bar,
    boxplot,
    colorbar,
    hbar,
    heatmap,
    interval,
    legend,
    scatter,
)

REPO = Path(__file__).resolve().parents[1]
DOCUMENTS = REPO / "tests" / "documents"
# The packages a test document loads, copied beside it as a paper vendors them:
# this package, two siblings, and the venue styles as the venues publish them.
PACKAGES = (
    REPO / "tex" / "latex" / "figmint" / "figmint.sty",
    REPO.parent / "macromint" / "tex" / "latex" / "macromint" / "macromint.sty",
    REPO.parent / "papermint" / "tex" / "latex" / "papermint" / "papermint.sty",
    *sorted((REPO / "tests" / "venues").glob("*.sty")),
)
BIG_POINTS_PER_POINT = 72.0 / 72.27
# Sub- and superscripts sit at most this many big points off the baseline of
# their line, far less than the distance to the next line.
SCRIPT_SHIFT = 4.0


def vendor(directory: Path) -> None:
    """Copy the packages beside a document, as a paper vendors them.

    Raises:
        FileNotFoundError: If a package is missing, such as a sibling checkout.
    """
    for package in PACKAGES:
        if not package.is_file():
            name = package.parents[3].name
            msg = f"{package} is missing: the tests need a checkout of {name}."
            raise FileNotFoundError(msg)

        shutil.copy(package, directory)


def place(name: str, directory: Path) -> Path:
    """Copy a test document into a directory, with the packages it loads beside it.

    Returns:
        The copy.
    """
    vendor(directory)

    return Path(shutil.copy(DOCUMENTS / f"{name}.tex", directory))


def compile_document(source: Path, engine: str) -> Path:
    """Compile a document in its directory, where its packages are.

    Returns:
        The PDF.

    Raises:
        RuntimeError: If the engine fails, with the end of the log.
    """
    completed = subprocess.run(  # noqa: S603
        [engine, "-interaction=nonstopmode", "-halt-on-error", source.name],
        cwd=source.parent,
        env={**os.environ, "max_print_line": "10000"},
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        log = source.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
        msg = f"{engine} failed on {source.name}:\n{log[-3000:]}"
        raise RuntimeError(msg)

    return source.with_suffix(".pdf")


def log_of(source: Path) -> str:
    return source.with_suffix(".log").read_text(encoding="utf-8", errors="replace")


def pages(pdf: Path) -> list[LTPage]:
    return list(extract_pages(pdf, laparams=LAParams()))


def chars(item: object) -> Iterator[LTChar]:
    """Yield the glyphs inside a layout item."""
    if isinstance(item, LTChar):
        yield item
    elif isinstance(item, LTContainer):
        for child in item:
            yield from chars(child)


def figures(page: LTPage) -> list[LTFigure]:
    """Return the included figures of a page: its form objects."""
    return [item for item in page if isinstance(item, LTFigure)]


def text_lines(item: object) -> Iterator[LTTextLine]:
    if isinstance(item, LTTextLine):
        yield item
    elif isinstance(item, LTContainer) and not isinstance(item, LTFigure):
        for child in item:
            yield from text_lines(child)


def baseline(char: LTChar) -> float:
    """Return the baseline of a glyph, from the origin of its text matrix.

    pdfminer builds a glyph's box from its font's descent, and the STIX Two
    math fonts declare one that puts their glyphs far below their line.
    """
    return char.matrix[5]


def caption_chars(page: LTPage, word: str) -> list[LTChar]:
    """Return the glyphs of the caption of a page that holds a word.

    pdfminer splits a caption into text lines where the fonts change, so the
    caption is every glyph outside the figures on the baseline of the line
    holding the word, scripts included, at or right of its start, which leaves
    out the line numbers of a draft ruler in the margin.

    Raises:
        ValueError: If the page does not hold exactly one line with the word.
    """
    lines = [line for line in text_lines(page) if word in line.get_text()]

    if len(lines) != 1:
        msg = (
            f"page {page.pageid} holds {len(lines)} lines with {word!r}, expected one."
        )
        raise ValueError(msg)

    (line,) = lines
    anchor = baseline(
        next(char for char in chars(line) if not char.get_text().isspace())
    )
    outside = [
        char for item in page if not isinstance(item, LTFigure) for char in chars(item)
    ]

    return [
        char
        for char in outside
        if not char.get_text().isspace()
        and char.x0 >= line.x0 - 1.0
        and abs(baseline(char) - anchor) <= SCRIPT_SHIFT
    ]


def font_of(char: LTChar) -> str:
    """Return the font of a glyph without its subset prefix and its optical size.

    Computer Modern and Latin Modern name the size in the font, as in CMR10
    and CMR7, and a caption at 10pt with a 7pt script uses both.
    """
    return re.sub(r"\d+", "", char.fontname.split("+")[-1])


def size_of(char: LTChar) -> float:
    """Return the font size of a glyph in big points.

    pdfminer reports the height of the glyph box, which for a rotated glyph is
    its advance; the width is its size then.
    """
    a, b, _, _, _, _ = char.matrix

    return char.width if abs(b) > abs(a) else char.height


STEPS = np.linspace(0.0, 80.0, 81)
RNG = np.random.default_rng(0)
SAMPLES = RNG.normal(size=(4, 40))


def _lines(_: Figure, axes: Axes) -> None:
    axes.errorbar(STEPS[::10], np.exp(-0.05 * STEPS[::10]), yerr=0.05, label="baseline")
    axes.plot(STEPS, 0.9 * np.exp(-0.08 * STEPS) - 0.1, label=r"ours, $x_{t}$")
    axes.set_xlabel(r"Step $t$")
    axes.set_ylabel(r"Loss $f(x_{t})$")
    legend(axes, loc="best")


def _log(_: Figure, axes: Axes) -> None:
    axes.plot(STEPS + 1.0, np.exp(-0.05 * STEPS) + 0.001, label="baseline")
    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlabel(r"Step $t$")
    axes.set_ylabel("Error")
    legend(axes, loc="best")


def _bars(_: Figure, axes: Axes) -> None:
    for index in range(3):
        bar(
            axes,
            [1, 2, 3],
            [0.5 + 0.1 * index, 0.7, 0.4],
            label=f"series {index}",
            group=(index, 3),
        )

    axes.set_xticks([1, 2, 3], ["A", "B", "C"])
    axes.set_ylabel("Score")
    legend(axes, loc="best")


def _hbars(_: Figure, axes: Axes) -> None:
    hbar(axes, [1, 2, 3], [0.5, 0.7, -0.4], label="score")
    axes.set_yticks([1, 2, 3], ["A", "B", "C"])
    axes.set_xlabel("Score")


def _scatter(_: Figure, axes: Axes) -> None:
    scatter(axes, SAMPLES[0], SAMPLES[1], label="points")
    axes.set_xlabel(r"$x_{1}$")
    axes.set_ylabel(r"$x_{2}$")
    legend(axes, loc="best")


def _heatmap(_: Figure, axes: Axes) -> None:
    values = np.linspace(0.0, 1.0, 400).reshape(20, 20)
    image = heatmap(axes, values, extent=(-1.0, 1.0, -1.0, 1.0), vmin=0.0, vmax=1.0)
    colorbar(axes, image)
    axes.set_xlabel("Width")
    axes.set_ylabel("Depth")


def _interval(_: Figure, axes: Axes) -> None:
    mean = np.exp(-0.05 * STEPS)
    (line,) = axes.plot(STEPS, mean, label="mean")
    interval(axes, STEPS, mean - 0.1, mean + 0.1, color=line.get_color())
    axes.set_xlabel(r"Step $t$")
    legend(axes, loc="best")


def _area(_: Figure, axes: Axes) -> None:
    area(axes, STEPS, np.exp(-0.05 * STEPS), label="density")
    axes.set_xlabel(r"$x$")
    legend(axes, loc="best")


def _boxes(_: Figure, axes: Axes) -> None:
    boxplot(axes, list(SAMPLES))
    axes.set_xticks([1, 2, 3, 4], ["A", "B", "C", "D"])
    axes.set_ylabel("Value")


def _grid(_: Figure, axes: np.ndarray) -> None:
    assert axes.shape == (2, 2)

    for index, panel in enumerate(axes.flat):
        panel.plot(STEPS, np.exp(-0.02 * (index + 1) * STEPS))
        panel.set_xlabel(r"Step $t$")


PLOTS = {
    "lines": _lines,
    "log": _log,
    "bars": _bars,
    "hbars": _hbars,
    "scatter": _scatter,
    "heatmap": _heatmap,
    "interval": _interval,
    "area": _area,
    "boxes": _boxes,
    "grid": _grid,
}


def register_plots(document: Document) -> None:
    """Register the plot of every figure the document asks for."""
    for name in document.names:
        document.figure(name)(PLOTS[name])
