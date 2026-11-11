"""Tables of results for the figure scripts, as tab-separated text."""

from os import PathLike
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike

VECTOR_RANK = 1
MATRIX_RANK = 2


def export_table(path: str | PathLike[str], **columns: ArrayLike) -> None:
    """Write named columns as a tab-separated table with a header line.

    One-dimensional columns of one length are written side by side. One
    two-dimensional column with one-dimensional ``x`` and ``y`` columns is
    written as a grid: one row per cell, with ``x`` changing fastest. Cells are
    written as Python prints them, so an integer in a column that also holds
    floats prints as ``0.0``.

    Raises:
        ValueError: If there is no column, a column is not one- or
            two-dimensional, the vectors differ in length, or the grid columns
            do not fit together.
    """
    if not columns:
        msg = "export_table requires at least one column."
        raise ValueError(msg)

    arrays = {name: np.asarray(value) for name, value in columns.items()}

    for name, array in arrays.items():
        if array.ndim not in {VECTOR_RANK, MATRIX_RANK}:
            msg = (
                f"Column {name!r} must be a vector or a matrix, "
                f"got shape {array.shape}."
            )
            raise ValueError(msg)

    matrices = [name for name, array in arrays.items() if array.ndim == MATRIX_RANK]

    if matrices:
        headers, rows = _grid_rows(matrices=matrices, arrays=arrays)
    else:
        headers, rows = tuple(arrays), _vector_rows(arrays)

    lines = ["\t".join(headers)]
    lines.extend("\t".join(str(cell) for cell in row) for row in rows)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _vector_rows(arrays: dict[str, np.ndarray]) -> list[list[object]]:
    lengths = {len(array) for array in arrays.values()}

    if len(lengths) != 1:
        msg = "All one-dimensional columns must have the same length."
        raise ValueError(msg)

    columns = [array.tolist() for array in arrays.values()]

    return [list(row) for row in zip(*columns, strict=True)]


def _grid_rows(
    *,
    matrices: list[str],
    arrays: dict[str, np.ndarray],
) -> tuple[tuple[str, str, str], list[list[object]]]:
    if len(matrices) != 1:
        msg = "Grid tables require exactly one two-dimensional value column."
        raise ValueError(msg)

    (name,) = matrices

    if set(arrays) != {"x", "y", name}:
        msg = "Grid tables require exactly the x, y, and value columns."
        raise ValueError(msg)

    x_values, y_values, matrix = (
        arrays["x"].tolist(),
        arrays["y"].tolist(),
        arrays[name],
    )

    if matrix.shape[0] != len(y_values):
        msg = "Grid value rows must match the y column length."
        raise ValueError(msg)

    if matrix.shape[1] != len(x_values):
        msg = "Grid value columns must match the x column length."
        raise ValueError(msg)

    cells = matrix.tolist()

    return (
        ("x", "y", name),
        [
            [x_value, y_value, cells[y_index][x_index]]
            for y_index, y_value in enumerate(y_values)
            for x_index, x_value in enumerate(x_values)
        ],
    )
