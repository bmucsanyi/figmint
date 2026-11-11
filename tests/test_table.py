"""Tests for the table export."""

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import ArrayLike

from figmint import export_table


def test_vectors_are_written_side_by_side(tmp_path: Path) -> None:
    path = tmp_path / "curve.tsv"

    export_table(path, x=[0, 1, 2], y=np.array([1.0, 0.5, 0.25]))

    assert path.read_text(encoding="utf-8") == "x\ty\n0\t1.0\n1\t0.5\n2\t0.25\n"


def test_an_integer_among_floats_is_written_as_a_float(tmp_path: Path) -> None:
    path = tmp_path / "mixed.tsv"

    export_table(path, y=[0, 1.5])

    assert path.read_text(encoding="utf-8") == "y\n0.0\n1.5\n"


def test_float32_values_keep_their_double_representation(tmp_path: Path) -> None:
    path = tmp_path / "single.tsv"

    export_table(path, y=np.array([0.1], dtype=np.float32))

    assert path.read_text(encoding="utf-8") == f"y\n{float(np.float32(0.1))}\n"


def test_strings_are_columns_too(tmp_path: Path) -> None:
    path = tmp_path / "names.tsv"

    export_table(path, name=["a", "b"], score=[1.0, 2.0])

    assert path.read_text(encoding="utf-8") == "name\tscore\na\t1.0\nb\t2.0\n"


def test_a_grid_is_written_with_x_changing_fastest(tmp_path: Path) -> None:
    path = tmp_path / "heatmap.tsv"

    export_table(
        path, x=np.array([10, 20]), y=[1, 2, 3], z=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    )

    assert path.read_text(encoding="utf-8") == (
        "x\ty\tz\n10\t1\t0.1\n20\t1\t0.2\n10\t2\t0.3\n20\t2\t0.4\n10\t3\t0.5\n20\t3\t0.6\n"
    )


@pytest.mark.parametrize(
    ("columns", "message"),
    [
        ({}, "at least one column"),
        ({"x": 1.0}, "vector or a matrix"),
        ({"x": np.zeros((2, 2, 2))}, "vector or a matrix"),
        ({"x": [0, 1], "y": [0.0]}, "same length"),
        ({"x": [0], "y": [0], "z": [[1]], "w": [[1]]}, "exactly one two-dimensional"),
        ({"x": [0], "t": [0], "z": [[1]]}, "exactly the x, y, and value"),
        ({"x": [0], "y": [0, 1], "z": [[1]]}, "y column length"),
        ({"x": [0, 1, 2], "y": [0, 1], "z": [[1, 2], [3, 4]]}, "x column length"),
    ],
)
def test_invalid_columns_fail_loudly(
    tmp_path: Path, columns: dict[str, ArrayLike], message: str
) -> None:
    path = tmp_path / "bad.tsv"

    with pytest.raises(ValueError, match=message):
        export_table(path, **columns)

    assert not path.exists()


def test_a_ragged_column_fails_in_numpy(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inhomogeneous"):
        export_table(tmp_path / "bad.tsv", x=[[1, 2], [3]])
