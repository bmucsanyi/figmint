"""Tests for the tick numbers of the look."""

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, LogFormatterSciNotation

from figmint._ticks import NumberFormatter, format_number, format_ticks

MINUS = "\N{MINUS SIGN}"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.5, "0.5"),
        (1.0, "1"),
        (2.50, "2.5"),
        (100.0, "100"),
        (1234567.0, "1234567"),
        (1e-5, "0.00001"),
        (0.1 + 0.2, "0.3"),
        (-2.0, MINUS + "2"),
        (-0.25, MINUS + "0.25"),
        (-0.0, "0"),
        (0.0, "0"),
    ],
)
def test_format_number(value: float, expected: str) -> None:
    assert format_number(value) == expected


def test_format_ticks_touches_only_linear_axes_with_the_default_formatter() -> None:
    figure = Figure()
    FigureCanvasAgg(figure)
    linear, log, custom = figure.subplots(1, 3)
    log.set_yscale("log")
    own = FuncFormatter(lambda value, _: f"{value:.3f}")
    custom.xaxis.set_major_formatter(own)

    format_ticks(figure)

    assert isinstance(linear.xaxis.get_major_formatter(), NumberFormatter)
    assert isinstance(linear.yaxis.get_major_formatter(), NumberFormatter)
    assert isinstance(log.xaxis.get_major_formatter(), NumberFormatter)
    assert isinstance(log.yaxis.get_major_formatter(), LogFormatterSciNotation)
    assert custom.xaxis.get_major_formatter() is own


def test_formatted_ticks_have_no_trailing_zeros() -> None:
    figure = Figure()
    canvas = FigureCanvasAgg(figure)
    axes = figure.subplots()
    axes.set_xticks([-1.0, 0.0, 0.5, 1.0])
    format_ticks(figure)
    canvas.draw()

    assert [label.get_text() for label in axes.get_xticklabels()] == [
        MINUS + "1",
        "0",
        "0.5",
        "1",
    ]
