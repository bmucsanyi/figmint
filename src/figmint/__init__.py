"""Matplotlib style API."""

from ._heatmap import export_heatmap
from ._legend import legend
from ._provenance import provenance, savefig
from ._style import register_fonts, style
from ._table import export_table

__all__ = [
    "export_heatmap",
    "export_table",
    "legend",
    "provenance",
    "register_fonts",
    "savefig",
    "style",
]
