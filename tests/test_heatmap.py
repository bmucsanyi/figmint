"""Tests for heatmap image export."""

import math
import re
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import ArrayLike
from PIL import Image

from figmint import export_heatmap

STY = Path(__file__).resolve().parents[1] / "tex" / "latex" / "figmint" / "figmint.sty"


def sty_colormap() -> list[tuple[float, ...]]:
    """Read the PGFPlots colormap ``figmint plasma`` from figmint.sty.

    Returns:
        The RGB entries of the colormap, in order.
    """
    source = STY.read_text(encoding="utf-8")
    block = re.search(r"colormap=\{figmint plasma\}\{%(.*?)\}", source, flags=re.DOTALL)
    assert block is not None

    return [
        tuple(float(channel) for channel in entry)
        for entry in re.findall(r"rgb=\(([^,]+),([^,]+),([^)]+)\)", block.group(1))
    ]


def pgfplots_color(
    value: float, *, vmin: float, vmax: float, entries: list[tuple[float, ...]]
) -> list[float]:
    """Color PGFPlots gives a point meta value under a colormap.

    Returns:
        The RGB color of the value after clipping it to ``[vmin, vmax]``, mapping
        it linearly onto the equally spaced entries, and interpolating linearly
        between the two neighboring entries.
    """
    fraction = min(max((value - vmin) / (vmax - vmin), 0.0), 1.0)
    position = fraction * (len(entries) - 1)
    index = min(math.floor(position), len(entries) - 2)
    weight = position - index

    return [
        (1.0 - weight) * low + weight * high
        for low, high in zip(entries[index], entries[index + 1], strict=True)
    ]


def test_export_heatmap_colors_values_like_the_pgfplots_colormap(
    tmp_path: Path,
) -> None:
    path = tmp_path / "heatmap.png"
    vmin, vmax = -1.0, 3.0
    step = (vmax - vmin) / 255.0
    values = [
        [-2.5, vmin, vmin + 0.5 * step, 0.0],
        [vmin + 128.0 * step, 1.234, vmin + 200.5 * step, 2.2],
        [vmin + 254.25 * step, vmax, 7.0, 0.77],
    ]
    entries = sty_colormap()

    export_heatmap(path, np.array(values), vmin=vmin, vmax=vmax)

    with Image.open(path) as image:
        assert image.mode == "RGB"
        pixels = np.asarray(image, dtype=float)

    expected = np.array([
        [pgfplots_color(value, vmin=vmin, vmax=vmax, entries=entries) for value in row]
        for row in reversed(values)
    ])

    assert len(entries) == 256
    assert pixels.shape == (3, 4, 3)
    assert np.abs(pixels - 255.0 * expected).max() <= 0.5 + 1e-6


@pytest.mark.parametrize(
    ("name", "values", "vmin", "vmax", "message"),
    [
        ("heatmap.jpg", [[0.0]], 0.0, 1.0, "PNG"),
        ("heatmap.png", [0.0, 1.0], 0.0, 1.0, "matrix"),
        ("heatmap.png", [[[0.0]]], 0.0, 1.0, "matrix"),
        ("heatmap.png", np.zeros((0, 3)), 0.0, 1.0, "matrix"),
        ("heatmap.png", [[0.0, math.nan]], 0.0, 1.0, "finite"),
        ("heatmap.png", [[0.0, math.inf]], 0.0, 1.0, "finite"),
        ("heatmap.png", [[0.0]], 1.0, 1.0, "vmin < vmax"),
        ("heatmap.png", [[0.0]], 0.0, math.inf, "vmin < vmax"),
    ],
)
def test_export_heatmap_rejects_invalid_input(
    tmp_path: Path,
    name: str,
    values: ArrayLike,
    vmin: float,
    vmax: float,
    message: str,
) -> None:
    path = tmp_path / name

    with pytest.raises(ValueError, match=message):
        export_heatmap(path, values, vmin=vmin, vmax=vmax)

    assert not path.exists()
