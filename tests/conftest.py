"""Shared test helpers."""

from collections.abc import Callable

import pytest
from matplotlib.axes import Axes


def _legend_columns(axis: Axes) -> int:
    """Count the columns of the drawn legend of an axes.

    Returns:
        The number of distinct left edges of the legend texts, which are left
        aligned within a column.
    """
    legend = axis.get_legend()
    assert legend is not None
    axis.figure.canvas.draw()

    return len({round(text.get_window_extent().x0, 3) for text in legend.get_texts()})


@pytest.fixture
def legend_columns() -> Callable[[Axes], int]:
    return _legend_columns
