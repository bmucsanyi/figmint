"""Heatmap image export for PGFPlots."""

import math
from os import PathLike
from pathlib import Path

import numpy as np
from matplotlib import colormaps
from numpy.typing import ArrayLike
from PIL import Image

from figmint._colors import COLORMAP
from figmint._table import MATRIX_RANK


def export_heatmap(
    path: str | PathLike[str],
    values: ArrayLike,
    *,
    vmin: float,
    vmax: float,
) -> None:
    r"""Write a scalar field as an RGB PNG for ``\addplot graphics``.

    Each value becomes one pixel. ``values[i, j]`` is the value at the ``j``-th x
    and the ``i``-th y, with y increasing with ``i``, so ``values[0, 0]`` is the
    lower left pixel. Each value is colored the way PGFPlots colors point meta
    under ``point meta min=vmin`` and ``point meta max=vmax``: clipped to
    ``[vmin, vmax]``, mapped linearly onto the entries of figmint's colormap, and
    interpolated linearly between neighboring entries. The image therefore
    matches a PGFPlots colorbar over the same range.

    Raises:
        ValueError: If the path does not end in ``.png``, if ``values`` is not a
            non-empty matrix of finite numbers, or if ``vmin`` and ``vmax`` are
            not finite with ``vmin < vmax``.
    """
    if Path(path).suffix.lower() != ".png":
        msg = f"export_heatmap writes PNG files, got {path!r}."
        raise ValueError(msg)

    field = np.asarray(values, dtype=float)

    if field.ndim != MATRIX_RANK or field.size == 0:
        msg = f"Heatmap values must be a non-empty matrix, got shape {field.shape}."
        raise ValueError(msg)

    if not np.isfinite(field).all():
        msg = "Heatmap values must be finite."
        raise ValueError(msg)

    if not (math.isfinite(vmin) and math.isfinite(vmax) and vmin < vmax):
        msg = f"Expected finite vmin < vmax, got vmin={vmin} and vmax={vmax}."
        raise ValueError(msg)

    colormap = colormaps[COLORMAP]
    entries = colormap(np.arange(colormap.N))[:, :3]
    position = np.clip((field - vmin) / (vmax - vmin), 0.0, 1.0) * (len(entries) - 1)
    lower = np.minimum(position.astype(int), len(entries) - 2)
    weight = (position - lower)[..., None]
    colors = (1.0 - weight) * entries[lower] + weight * entries[lower + 1]
    pixels = np.rint(np.iinfo(np.uint8).max * colors[::-1]).astype(np.uint8)
    Image.fromarray(pixels).save(path, optimize=True)
