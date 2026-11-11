"""Figures drawn with matplotlib to what the document asks for."""

from figmint._document import Document
from figmint._legend import legend
from figmint._plots import (
    area,
    bar,
    boxplot,
    colorbar,
    hbar,
    heatmap,
    interval,
    scatter,
)
from figmint._provenance import provenance, savefig
from figmint._style import style
from figmint._table import export_table

__all__ = [
    "Document",
    "area",
    "bar",
    "boxplot",
    "colorbar",
    "export_table",
    "hbar",
    "heatmap",
    "interval",
    "legend",
    "provenance",
    "savefig",
    "scatter",
    "style",
]
