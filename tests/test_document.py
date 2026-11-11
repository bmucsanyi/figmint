"""Tests for Document: the file, staleness, the probe, and the record in the PDF."""

from pathlib import Path

import pytest
from documents import REPO, compile_document, place, register_plots, vendor
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.utils import decode_text

from figmint import Document

TWO_FIGURES = r"""\documentclass{article}
\usepackage{figmint}

\begin{document}

\begin{figure}
  \centering
  \figmintgraphic{first}
  \caption{First.}
\end{figure}

\begin{figure}
  \centering
  \figmintgraphic[width fraction=FRACTION]{second}
  \caption{Second.}
\end{figure}

\end{document}
"""


def compiled_times(directory: Path) -> Path:
    """Compile the article with times.

    Returns:
        Its .figmint file.
    """
    source = place("times", directory)
    compile_document(source, "pdflatex")

    return source.with_suffix(".figmint")


def metadata(pdf: Path) -> dict[str, str]:
    with pdf.open("rb") as handle:
        info = PDFDocument(PDFParser(handle)).info[0]

    return {
        key: decode_text(value)
        for key, value in info.items()
        if isinstance(value, bytes)
    }


def draw_nothing(_: Figure, axes: Axes) -> None:
    axes.plot([0.0, 1.0], [0.0, 1.0])


def test_another_version_stops(tmp_path: Path) -> None:
    file = compiled_times(tmp_path)
    file.write_text(file.read_text().replace("figmint=0.2.1", "figmint=9.9.9"))

    with pytest.raises(ValueError, match=r"written by figmint 9\.9\.9"):
        Document(file, results="results/run")


def test_repeated_identical_lines_are_accepted(tmp_path: Path) -> None:
    file = compiled_times(tmp_path)
    (line,) = [
        line for line in file.read_text().splitlines() if line.startswith("figure=")
    ]
    file.write_text(file.read_text() + line + "\n")

    assert Document(file, results="results/run").names == ["lines"]


def test_two_sizes_for_one_name_are_rejected(tmp_path: Path) -> None:
    file = compiled_times(tmp_path)
    (line,) = [
        line for line in file.read_text().splitlines() if line.startswith("figure=")
    ]
    file.write_text(file.read_text() + line.replace("width=345", "width=300") + "\n")

    with pytest.raises(ValueError, match="two different ways"):
        Document(file, results="results/run")


def test_an_unknown_family_is_rejected(tmp_path: Path) -> None:
    file = compiled_times(tmp_path)
    file.write_text(file.read_text().replace("family=serif", "family=unknown"))

    with pytest.raises(ValueError, match="three family defaults"):
        Document(file, results="results/run")


def test_figure_rejects_a_name_the_document_does_not_ask_for(tmp_path: Path) -> None:
    document = Document(compiled_times(tmp_path), results="results/run")

    with pytest.raises(ValueError, match="does not ask for a figure named 'nope'"):
        document.figure("nope")


def test_main_stops_for_a_line_without_a_function(tmp_path: Path) -> None:
    document = Document(compiled_times(tmp_path), results="results/run")

    with pytest.raises(ValueError, match=r"No function draws \['lines'\]"):
        document.main([])


def test_main_stops_for_a_name_not_in_the_file(tmp_path: Path) -> None:
    document = Document(compiled_times(tmp_path), results="results/run")

    with pytest.raises(ValueError, match="does not ask for figures named"):
        document.main(["nope"])


def test_a_second_main_draws_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = Document(compiled_times(tmp_path), results="results/run", repo=REPO)
    register_plots(document)
    document.main([])
    pdf = tmp_path / "figures" / "lines.pdf"
    drawn = pdf.stat().st_mtime_ns
    document.main([])

    assert capsys.readouterr().out.splitlines() == ["Drew lines.", "Nothing to draw."]
    assert pdf.stat().st_mtime_ns == drawn


def test_only_the_figure_whose_line_changed_is_redrawn(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vendor(tmp_path)
    source = tmp_path / "two.tex"
    source.write_text(TWO_FIGURES.replace("FRACTION", "1.0"))
    compile_document(source, "pdflatex")
    document = Document(
        source.with_suffix(".figmint"), results="results/run", repo=REPO
    )
    document.figure("first")(draw_nothing)
    document.figure("second")(draw_nothing)
    document.main([])
    first = tmp_path / "figures" / "first.pdf"
    drawn = first.stat().st_mtime_ns

    source.write_text(TWO_FIGURES.replace("FRACTION", "0.5"))
    compile_document(source, "pdflatex")
    document = Document(
        source.with_suffix(".figmint"), results="results/run", repo=REPO
    )
    document.figure("first")(draw_nothing)
    document.figure("second")(draw_nothing)
    document.main([])

    assert capsys.readouterr().out.splitlines() == [
        "Drew first, second.",
        "Drew second.",
    ]
    assert first.stat().st_mtime_ns == drawn

    document.main(["--all"])

    assert capsys.readouterr().out.splitlines() == ["Drew first, second."]
    assert first.stat().st_mtime_ns > drawn


def test_the_probe_stops_when_the_lines_give_other_fonts(tmp_path: Path) -> None:
    file = compiled_times(tmp_path)
    file.write_text(
        file.read_text().replace("preamble=\\renewcommand{\\rmdefault}{ptm}\n", "")
    )
    document = Document(file, results="results/run", repo=REPO)
    register_plots(document)

    with pytest.raises(RuntimeError, match="do not reproduce") as error:
        document.main([])

    assert "ptmr7t" in str(error.value)
    assert "cmr" in str(error.value)
    assert not (tmp_path / "figures").exists()


def test_the_probe_stops_when_the_deck_font_line_is_missing(tmp_path: Path) -> None:
    source = place("deck", tmp_path)
    compile_document(source, "lualatex")
    file = source.with_suffix(".figmint")
    file.write_text(
        file.read_text().replace("preamble=\\usepackage {slidemintfonts}\n", "")
    )
    document = Document(file, results="results/run", repo=REPO)
    register_plots(document)

    with pytest.raises(RuntimeError, match="do not reproduce") as error:
        document.main([])

    assert "Roboto Condensed Light" in str(error.value)
    assert not (tmp_path / "figures").exists()


def test_the_pdf_records_the_line_and_the_provenance_through_the_pgf_canvas(
    tmp_path: Path,
) -> None:
    document = Document(compiled_times(tmp_path), results="results/run_3", repo=REPO)
    register_plots(document)
    document.main([])
    found = metadata(tmp_path / "figures" / "lines.pdf")

    assert found["Creator"] == "figmint"
    assert found["Subject"].startswith("repo=figmint commit=")
    assert found["Subject"].endswith(" results=results/run_3")
    assert found["Keywords"].startswith(document.lines["lines"].text + ";setup=")
