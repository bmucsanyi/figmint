"""Tick numbers by the look: no trailing zeros, and a real minus sign."""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import Formatter, ScalarFormatter

# Tick locators leave floating point noise, which rounding to this many decimals
# removes.
DECIMALS = 10


def format_number(value: float) -> str:
    r"""Return a number with no trailing zeros and U+2212 as its minus sign.

    The digits and the decimal point are plain text, so a document sets them in
    its text font; the pgf backend sets U+2212 as ``\ensuremath{-}``, in the
    math font.

    Returns:
        The number as text.
    """
    rounded = round(value, DECIMALS)
    text = np.format_float_positional(abs(rounded), trim="-")

    if rounded < 0:
        return "\N{MINUS SIGN}" + text

    return text


class NumberFormatter(Formatter):
    """Formats ticks through ``format_number``."""

    def __call__(self, x: float, pos: int | None = None) -> str:  # noqa: ARG002
        return format_number(x)


def format_ticks(figure: Figure) -> None:
    r"""Give every linear axis with matplotlib's formatter the formatter of the look.

    A log axis keeps matplotlib's formatter, whose exponents the document sets
    through ``\mathdefault``, and an axis with a formatter of its own keeps it.
    """
    for axes in figure.axes:
        for axis in (axes.xaxis, axes.yaxis):
            linear = axis.get_scale() == "linear"

            if linear and isinstance(axis.get_major_formatter(), ScalarFormatter):
                axis.set_major_formatter(NumberFormatter())
