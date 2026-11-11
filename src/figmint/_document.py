"""Drawing the figures a document asks for, from the file it wrote."""

import hashlib
import os
import subprocess  # noqa: S404  # the engine named by the document, on a file this module wrote
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version
from os import PathLike
from pathlib import Path
from typing import Any

import matplotlib as mpl
from matplotlib.backends.backend_pgf import FigureCanvasPgf
from matplotlib.figure import Figure
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.utils import decode_text

from figmint._provenance import provenance, save
from figmint._style import font_sizes, look

TEX_POINTS_PER_INCH = 72.27
FAMILY_COMMANDS = {
    "serif": r"\rmfamily",
    "sans-serif": r"\sffamily",
    "monospace": r"\ttfamily",
}
PROBED_FIELDS = ("fonts", "script", "scriptscript")

# A drawing function receives the figure and the axes of figure.subplots(rows, cols):
# one Axes for a single panel, an array of them for a grid.
Drawer = Callable[[Figure, Any], None]


@dataclass(frozen=True)
class Line:
    """What the document asks for one figure: the fields of its line in the file."""

    name: str
    width: float
    height: float
    rows: int
    cols: int
    theme: str
    size: float
    script: str
    scriptscript: str
    family: str
    series: str
    shape: str
    fonts: str
    text: str


def parse_line(value: str) -> Line:
    """Parse the value of a ``figure=`` line.

    The ``fonts`` field comes last and holds semicolons of its own, so it is
    split off first.

    Returns:
        The line.
    """
    name, _, rest = value.partition(";")
    head, _, fonts = rest.partition(";fonts=")
    fields = dict(part.partition("=")[::2] for part in head.split(";"))

    return Line(
        name=name,
        width=float(fields["width"]),
        height=float(fields["height"]),
        rows=int(fields["rows"]),
        cols=int(fields["cols"]),
        theme=fields["theme"],
        size=float(fields["size"]),
        script=fields["script"],
        scriptscript=fields["scriptscript"],
        family=fields["family"],
        series=fields["series"],
        shape=fields["shape"],
        fonts=fonts,
        text="figure=" + value,
    )


class Document:
    """The figures of one document, drawn to the file the document wrote.

    A figure script registers one function per figure name with ``figure``
    and calls ``main``. Each figure is drawn at the size, the font size, the
    family, and the theme of its line, with the engine and the preamble lines
    of the file, and saved as ``<directory>/<name>.pdf`` with the line it was
    drawn for in its metadata.

    Args:
        path: The ``.figmint`` file of the document.
        results: The directory of the results the figures are drawn from,
            recorded in every figure.
        repo: A directory inside the repository to record, as in ``savefig``.

    Raises:
        ValueError: If the file was written by another version of figmint, a
            figure has two different lines, or a line has a family that
            matplotlib cannot select.
    """

    def __init__(
        self,
        path: str | PathLike[str],
        *,
        results: str | PathLike[str],
        repo: str | PathLike[str] | None = None,
    ) -> None:
        self.path = Path(path)
        self.results = results
        self.repo = repo
        self.preamble: list[str] = []
        self.lines: dict[str, Line] = {}
        self._functions: dict[str, Drawer] = {}
        header = {}

        for raw in self.path.read_text(encoding="utf-8").splitlines():
            key, _, value = raw.partition("=")

            if key == "preamble":
                self.preamble.append(value)
            elif key == "figure":
                self._add(parse_line(value))
            else:
                header[key] = value

        for key in ("figmint", "engine", "directory"):
            if key not in header:
                msg = f"{self.path} has no {key} line."
                raise ValueError(msg)

        if header["figmint"] != version("figmint"):
            msg = (
                f"{self.path} was written by figmint {header['figmint']}, "
                f"and this is figmint {version('figmint')}."
            )
            raise ValueError(msg)

        self.engine = header["engine"]
        self.directory = self.path.parent / header["directory"]
        setup = "\n".join([header["figmint"], self.engine, *self.preamble])
        self._setup = hashlib.sha256(setup.encode("utf-8")).hexdigest()[:16]

    def _add(self, line: Line) -> None:
        if line.family not in FAMILY_COMMANDS:
            msg = (
                f"The caption font of figure {line.name!r} is none of the document's "
                "three family defaults, which are the families matplotlib can select."
            )
            raise ValueError(msg)

        if line.name in self.lines and self.lines[line.name] != line:
            msg = f"The document asks for figure {line.name!r} in two different ways."
            raise ValueError(msg)

        self.lines[line.name] = line

    @property
    def names(self) -> list[str]:
        """The figure names of the document, in the order of their first line."""
        return list(self.lines)

    def figure(self, name: str) -> Callable[[Drawer], Drawer]:
        """Register the function that draws a figure of the document.

        The function receives the figure and the axes of
        ``figure.subplots(rows, cols)`` with the grid of the figure's line.

        Returns:
            The decorator that registers the function.

        Raises:
            ValueError: If the document does not ask for a figure of that name.
        """
        if name not in self.lines:
            msg = f"The document does not ask for a figure named {name!r}."
            raise ValueError(msg)

        def register(function: Drawer) -> Drawer:
            self._functions[name] = function

            return function

        return register

    def main(self, argv: Sequence[str] | None = None) -> None:
        """Draw the figures whose line changed since they were drawn.

        Args:
            argv: Figure names to consider, or every name of the file when
                empty; ``--all`` draws them whether their line changed or not.
                Defaults to the command line.

        Raises:
            ValueError: If a name is not in the file or has no function.
        """
        arguments = list(sys.argv[1:] if argv is None else argv)
        everything = "--all" in arguments
        names = [
            argument for argument in arguments if argument != "--all"
        ] or self.names
        unknown = [name for name in names if name not in self.lines]

        if unknown:
            msg = f"The document does not ask for figures named {unknown}."
            raise ValueError(msg)

        undrawn = [name for name in names if name not in self._functions]

        if undrawn:
            msg = f"No function draws {undrawn}."
            raise ValueError(msg)

        stale = [
            name
            for name in names
            if everything or self._recorded(name) != self._record(name)
        ]

        if not stale:
            print("Nothing to draw.")

            return

        with _texinputs(self.path.parent):
            for line in _one_per_font_setup([self.lines[name] for name in stale]):
                self._probe(line)

            for name in stale:
                self._draw(name)

        print("Drew " + ", ".join(stale) + ".")

    def _record(self, name: str) -> str:
        """Return the line of a figure and the digest of the document-level lines."""
        return f"{self.lines[name].text};setup={self._setup}"

    def _recorded(self, name: str) -> str | None:
        """Return the record the figure's PDF carries, or None if it has none."""
        pdf = self.directory / f"{name}.pdf"

        if not pdf.exists():
            return None

        with pdf.open("rb") as handle:
            info = PDFDocument(PDFParser(handle)).info

        if not info or "Keywords" not in info[0]:
            return None

        return decode_text(info[0]["Keywords"])

    def _probe(self, line: Line) -> None:
        """Compile the preamble as matplotlib will and compare the fonts it gives.

        Raises:
            RuntimeError: If the probe does not compile, or the lines give
                other fonts or script sizes than the document has.
        """
        shape = r"\itshape" if line.shape == "it" else ""
        series = r"\bfseries" if line.series.startswith("b") else ""
        source = "\n".join([
            r"\documentclass{article}",
            r"\def\mathdefault#1{#1}",
            r"\everymath=\expandafter{\the\everymath\displaystyle}",
            rf"\usepackage[fontsize={line.size:f}pt]{{scrextend}}",
            *self.preamble,
            *_figmint_lines(line),
            r"\usepackage[strings]{underscore}",
            r"\makeatletter",
            r"\newwrite\probefile",
            r"\begin{document}",
            r"\immediate\openout\probefile=probe.out\relax",
            (
                "{"
                + FAMILY_COMMANDS[line.family]
                + rf"\fontsize{{{line.size:f}}}{{{1.2 * line.size:f}}}"
                + shape
                + series
                + r"\selectfont"
            ),
            r"\setbox0\hbox{$ $}",
            (
                r"\immediate\write\probefile{script=\sf@size;scriptscript=\ssf@size;"
                r"fonts=\fontname\font|\fontname\textfont0|\fontname\textfont1"
                r"|\fontname\textfont2|\fontname\textfont3}"
            ),
            "}",
            r"\immediate\closeout\probefile",
            r"x\end{document}",
        ])

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "probe.tex").write_text(source, encoding="utf-8")
            subprocess.run(  # noqa: S603
                [
                    self.engine,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "probe.tex",
                ],
                cwd=directory,
                capture_output=True,
                check=False,
            )
            result = Path(directory, "probe.out")

            if not result.exists():
                log = Path(directory, "probe.log").read_text(
                    encoding="utf-8", errors="replace"
                )
                msg = f"The probe compile with {self.engine} failed:\n{log[-2000:]}"
                raise RuntimeError(msg)

            found = result.read_text(encoding="utf-8").strip()

        head, _, fonts = found.partition(";fonts=")
        probed = dict(part.partition("=")[::2] for part in head.split(";"))
        probed["fonts"] = fonts
        differences = [
            f"  {field}: the document has {getattr(line, field)!r}, "
            f"the lines give {probed[field]!r}"
            for field in PROBED_FIELDS
            if probed[field] != getattr(line, field)
        ]

        if differences:
            msg = (
                "The preamble lines do not reproduce the document's fonts.\n"
                + "\n".join(differences)
            )
            raise RuntimeError(msg)

    def _draw(self, name: str) -> None:
        line = self.lines[name]
        params = {
            **look(line.theme),
            **font_sizes(line.size),
            "figure.figsize": (
                line.width / TEX_POINTS_PER_INCH,
                line.height / TEX_POINTS_PER_INCH,
            ),
            "font.family": line.family,
            "font.style": "italic" if line.shape == "it" else "normal",
            "font.weight": "bold" if line.series.startswith("b") else "normal",
            "text.usetex": False,
            "pgf.texsystem": self.engine,
            "pgf.rcfonts": False,
            "pgf.preamble": "\n".join([*self.preamble, *_figmint_lines(line)]),
        }

        with mpl.rc_context(params):
            figure = Figure()
            FigureCanvasPgf(figure)
            axes = figure.subplots(line.rows, line.cols)
            self._functions[name](figure, axes)
            self.directory.mkdir(parents=True, exist_ok=True)
            metadata = {
                **provenance(results=self.results, repo=self.repo),
                "Keywords": self._record(name),
            }
            save(figure, self.directory / f"{name}.pdf", metadata)


def _figmint_lines(line: Line) -> list[str]:
    """Return the lines figmint adds after the document's.

    The first pins the script sizes: matplotlib's own preamble loads scrextend
    with the size as ``9.000000pt``, after which LuaLaTeX with unicode-math
    sets the scripts of a 9pt figure at 6.3pt and 4.5pt. The second removes
    the page number: matplotlib typesets the figure as a page of an article,
    whose number would stand below the figure's box, clipped but in the file.
    Tick labels are formulas, as matplotlib writes them, and need nothing else.
    """
    return [
        (
            rf"\DeclareMathSizes{{{line.size:f}}}{{{line.size:g}}}"
            rf"{{{line.script}}}{{{line.scriptscript}}}"
        ),
        r"\pagestyle{empty}",
    ]


def _one_per_font_setup(lines: list[Line]) -> list[Line]:
    """Return one line per distinct fonts and script sizes, in order of appearance."""
    chosen = {}

    for line in lines:
        chosen.setdefault((line.fonts, line.script, line.scriptscript), line)

    return list(chosen.values())


@contextmanager
def _texinputs(directory: Path) -> Iterator[None]:
    """Let the engine find the packages beside the document while figures are drawn.

    matplotlib and the probe compile in temporary directories, so the
    document's directory, where a paper vendors its packages, is put first on
    TEXINPUTS for the time of the drawing.
    """
    before = os.environ.get("TEXINPUTS")
    os.environ["TEXINPUTS"] = f"{directory}{os.pathsep}{before or ''}"

    try:
        yield
    finally:
        if before is None:
            del os.environ["TEXINPUTS"]
        else:
            os.environ["TEXINPUTS"] = before
