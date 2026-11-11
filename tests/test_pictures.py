"""The bar for a figure, checked on compiled documents: the fonts and the size."""

from pathlib import Path

import pytest
from documents import (
    BIG_POINTS_PER_POINT,
    REPO,
    caption_chars,
    chars,
    compile_document,
    figures,
    font_of,
    log_of,
    pages,
    place,
    register_plots,
    size_of,
)
from pdfminer.layout import LTChar, LTPage

from figmint import Document

VENUES = [
    ("icml", "pdflatex"),
    ("neurips", "pdflatex"),
    ("iclr", "pdflatex"),
    ("xelatex", "xelatex"),
]
BOX_TOLERANCE = 0.01
SIZE_TOLERANCE = 0.05
# A caret where a superscript belongs, as a character or as an accent.
CARETS = {"^", "\N{MODIFIER LETTER CIRCUMFLEX ACCENT}"}
MINUS_SIGNS = {"-", "\N{MINUS SIGN}"}
# A digit that follows a minus sign starts within this many big points of it.
GLYPH_GAP = 2.0


def draw(name: str, engine: str, directory: Path) -> tuple[Document, Path]:
    """Compile a test document, draw its figures, and compile again.

    Returns:
        The document and the PDF.
    """
    source = place(name, directory)
    compile_document(source, engine)
    document = Document(
        source.with_suffix(".figmint"), results="results/run", repo=REPO
    )
    register_plots(document)
    document.main(["--all"])
    pdf = compile_document(source, engine)
    assert "Package figmint Warning" not in log_of(source)

    return document, pdf


def sizes(page: LTPage, word: str) -> set[float]:
    return {round(size_of(char), 2) for char in caption_chars(page, word)}


def fonts(page: LTPage, word: str) -> set[str]:
    return {font_of(char) for char in caption_chars(page, word)}


def digit_fonts(glyphs: list[LTChar]) -> set[str]:
    return {font_of(char) for char in glyphs if char.get_text().isdigit()}


def minus_fonts(glyphs: list[LTChar]) -> set[str]:
    return {font_of(char) for char in glyphs if char.get_text() in MINUS_SIGNS}


def math_digit_fonts(caption: list[LTChar]) -> set[str]:
    """Return the fonts of the caption's digits that follow a minus sign: its $-1$."""
    minuses = [char for char in caption if char.get_text() in MINUS_SIGNS]

    return {
        font_of(char)
        for char in caption
        if char.get_text().isdigit()
        and any(0.0 <= char.x0 - minus.x1 <= GLYPH_GAP for minus in minuses)
    }


def assert_sizes_in(found: set[float], allowed: set[float]) -> None:
    for size in found:
        assert any(abs(size - other) <= SIZE_TOLERANCE for other in allowed), (
            found,
            allowed,
        )


@pytest.mark.parametrize(("name", "engine"), VENUES)
def test_figures_have_the_fonts_and_the_size_of_their_captions(
    tmp_path: Path, name: str, engine: str
) -> None:
    document, pdf = draw(name, engine, tmp_path)
    seen = set()

    for page in pages(pdf):
        included = figures(page)

        if not included:
            continue

        caption_fonts, caption_sizes = fonts(page, "Caption"), sizes(page, "Caption")
        assert caption_fonts
        assert caption_sizes
        caption = caption_chars(page, "Caption")
        assert math_digit_fonts(caption)
        assert minus_fonts(caption)

        for figure in included:
            matching = {
                line.name
                for line in document.lines.values()
                if abs(figure.width - line.width * BIG_POINTS_PER_POINT)
                <= BOX_TOLERANCE
                and abs(figure.height - line.height * BIG_POINTS_PER_POINT)
                <= BOX_TOLERANCE
            }
            assert matching, (
                f"page {page.pageid}: box {figure.width} by {figure.height} bp"
            )
            seen |= matching
            glyphs = list(chars(figure))
            assert glyphs
            assert {font_of(char) for char in glyphs} <= caption_fonts
            found = {round(size_of(char), 2) for char in glyphs}
            assert_sizes_in(found, caption_sizes)
            # Tick numbers are formulas: their digits and minus signs come from
            # the math font, like the caption's $-1$, never from the text font.
            assert digit_fonts(glyphs)
            assert digit_fonts(glyphs) <= math_digit_fonts(caption), (
                digit_fonts(glyphs),
                math_digit_fonts(caption),
            )
            assert minus_fonts(glyphs) <= minus_fonts(caption), (
                minus_fonts(glyphs),
                minus_fonts(caption),
            )

            if matching == {"sublog"}:
                # Minor ticks are labeled, as matplotlib's 2 x 10^0.
                assert "\N{MULTIPLICATION SIGN}" in {char.get_text() for char in glyphs}

            if matching == {"log"}:
                # The exponents of the tick labels are digits at script size.
                assert min(found) < max(found) - 1.0
                assert not {char.get_text() for char in glyphs} & CARETS

    assert seen == set(document.lines)


@pytest.mark.parametrize(
    ("name", "word", "other"),
    [
        ("times", "Caption", None),
        ("ieeetran", "Caption", None),
        ("subfigure", "Subcaption", "Caption"),
    ],
)
def test_figure_text_has_the_size_of_the_caption_beside_it(
    tmp_path: Path, name: str, word: str, other: str | None
) -> None:
    _, pdf = draw(name, "pdflatex", tmp_path)
    (page,) = [page for page in pages(pdf) if figures(page)]
    (figure,) = figures(page)
    found = {round(size_of(char), 2) for char in chars(figure)}
    assert_sizes_in(found, sizes(page, word))

    if other is not None:
        assert max(found) < max(sizes(page, other))
