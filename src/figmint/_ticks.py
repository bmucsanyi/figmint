"""Tick numbers by the look: in math mode, with no trailing zeros."""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import Formatter, ScalarFormatter

# Tick locators leave floating point noise, which rounding to this many decimals
# removes.
DECIMALS = 10


def format_number(value: float) -> str:
    """Return a number with no trailing zeros and U+2212 as its minus sign.

    Returns:
        The number as text.
    """
    rounded = round(value, DECIMALS)
    text = np.format_float_positional(abs(rounded), trim="-")

    if rounded < 0:
        return "\N{MINUS SIGN}" + text

    return text


class NumberFormatter(Formatter):
    r"""Formats ticks through ``format_number``, in math mode.

    A label is ``$\mathdefault{...}$``, as matplotlib's own formatters write
    it. A document typesets it as a formula, so the digits and the minus sign
    come from its math font, as pgfplots and siunitx set numbers. matplotlib's
    own renderer sets ``\mathdefault`` in the label's font.
    """

    def __call__(self, x: float, pos: int | None = None) -> str:  # noqa: ARG002
        return rf"$\mathdefault{{{format_number(x)}}}$"


def format_ticks(figure: Figure) -> None:
    """Give every linear axis with matplotlib's formatter the formatter of the look.

    A log axis keeps matplotlib's formatter, which writes its labels in math
    mode already, and an axis with a formatter of its own keeps it.
    """
    for axes in figure.axes:
        for axis in (axes.xaxis, axes.yaxis):
            linear = axis.get_scale() == "linear"

            if linear and isinstance(axis.get_major_formatter(), ScalarFormatter):
                axis.set_major_formatter(NumberFormatter())
