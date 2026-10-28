"""Numeric table export for PGFPlots."""

from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import Protocol, runtime_checkable

VECTOR_RANK = 1
MATRIX_RANK = 2


@runtime_checkable
class _SupportsToList(Protocol):
    """Array-like object exposing Python lists."""

    def tolist(self) -> object:
        """Return a Python scalar or nested Python lists."""


def export_table(path: str | PathLike[str], **columns: object) -> None:
    """Write named columns as a tab-separated PGFPlots input table.

    Raises:
        ValueError: If the column shapes do not define a vector or grid table.
    """
    if not columns:
        msg = "export_table requires at least one column."
        raise ValueError(msg)

    values = {name: _python_value(value) for name, value in columns.items()}
    matrix_names = [
        name
        for name, value in values.items()
        if _rank(name=name, value=value) == MATRIX_RANK
    ]

    if matrix_names:
        headers, rows = _grid_rows(matrix_names=matrix_names, columns=values)
    else:
        headers, rows = tuple(values), _rows_from_vectors(columns=values)

    lines = ["\t".join(headers)]
    lines.extend("\t".join(str(cell) for cell in row) for row in rows)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rank(*, name: str, value: object) -> int:
    if _is_scalar(value):
        msg = f"Column {name!r} must be one- or two-dimensional."
        raise ValueError(msg)

    sequence = _sequence(name=name, value=value)

    if not sequence:
        return VECTOR_RANK

    first_is_scalar = _is_scalar(sequence[0])

    for item in sequence:
        if _is_scalar(item) != first_is_scalar:
            msg = f"Column {name!r} has mixed rank."
            raise ValueError(msg)

    return VECTOR_RANK if first_is_scalar else MATRIX_RANK


def _python_value(value: object) -> object:
    if isinstance(value, _SupportsToList):
        return value.tolist()

    return value


def _is_scalar(value: object) -> bool:
    return isinstance(value, str | bytes | bytearray) or not isinstance(value, Sequence)


def _sequence(*, name: str, value: object) -> Sequence[object]:
    if isinstance(value, str | bytes | bytearray) or not isinstance(value, Sequence):
        msg = f"Column {name!r} must be a sequence."
        raise TypeError(msg)

    return value


def _vector(*, name: str, value: object) -> list[object]:
    sequence = _sequence(name=name, value=value)

    for item in sequence:
        if not _is_scalar(item):
            msg = f"Column {name!r} must be one-dimensional."
            raise ValueError(msg)

    return list(sequence)


def _matrix(*, name: str, value: object) -> list[list[object]]:
    sequence = _sequence(name=name, value=value)
    rows = []
    width = None

    for row in sequence:
        row_sequence = _sequence(name=name, value=row)

        if width is None:
            width = len(row_sequence)
        elif len(row_sequence) != width:
            msg = f"Column {name!r} must be rectangular."
            raise ValueError(msg)

        for item in row_sequence:
            if not _is_scalar(item):
                msg = f"Column {name!r} must be at most two-dimensional."
                raise ValueError(msg)

        rows.append(list(row_sequence))

    return rows


def _rows_from_vectors(*, columns: dict[str, object]) -> list[list[object]]:
    vectors = {name: _vector(name=name, value=value) for name, value in columns.items()}
    lengths = {len(vector) for vector in vectors.values()}

    if len(lengths) != 1:
        msg = "All one-dimensional columns must have the same length."
        raise ValueError(msg)

    return [
        [vector[index] for vector in vectors.values()]
        for index in range(next(iter(lengths)))
    ]


def _grid_rows(
    *,
    matrix_names: list[str],
    columns: dict[str, object],
) -> tuple[tuple[str, str, str], list[list[object]]]:
    if len(matrix_names) != 1:
        msg = "Grid tables require exactly one two-dimensional value column."
        raise ValueError(msg)

    matrix_name = matrix_names[0]

    if set(columns) != {"x", "y", matrix_name}:
        msg = "Grid tables require exactly the x, y, and value columns."
        raise ValueError(msg)

    x_values = _vector(name="x", value=columns["x"])
    y_values = _vector(name="y", value=columns["y"])
    matrix = _matrix(name=matrix_name, value=columns[matrix_name])

    if len(matrix) != len(y_values):
        msg = "Grid value rows must match the y column length."
        raise ValueError(msg)

    for row in matrix:
        if len(row) != len(x_values):
            msg = "Grid value columns must match the x column length."
            raise ValueError(msg)

    return (
        ("x", "y", matrix_name),
        [
            [x_value, y_value, matrix[y_index][x_index]]
            for y_index, y_value in enumerate(y_values)
            for x_index, x_value in enumerate(x_values)
        ],
    )
