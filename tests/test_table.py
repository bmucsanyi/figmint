"""Tests for PGFPlots table export."""

from pathlib import Path

import pytest

from figmint import export_table


class ArrayLike:
    def __init__(self, value: object) -> None:
        self.value = value

    def tolist(self) -> object:
        return self.value


def test_export_table_writes_named_vector_columns(tmp_path: Path) -> None:
    path = tmp_path / "curve.tsv"

    export_table(path, x=[0, 1, 2], y=[1.0, 0.5, 0.25])

    assert path.read_text(encoding="utf-8") == "x\ty\n0\t1.0\n1\t0.5\n2\t0.25\n"


def test_export_table_writes_error_and_interval_columns(tmp_path: Path) -> None:
    path = tmp_path / "interval.tsv"

    export_table(
        path,
        x=[0, 1],
        y=[0.4, 0.6],
        yerr=[0.05, 0.08],
        ymin=[0.3, 0.45],
        ymax=[0.5, 0.75],
    )

    assert path.read_text(encoding="utf-8") == (
        "x\ty\tyerr\tymin\tymax\n0\t0.4\t0.05\t0.3\t0.5\n1\t0.6\t0.08\t0.45\t0.75\n"
    )


def test_export_table_flattens_grid_with_y_major_order(tmp_path: Path) -> None:
    path = tmp_path / "heatmap.tsv"

    export_table(
        path,
        x=ArrayLike([10, 20]),
        y=ArrayLike([1, 2, 3]),
        z=ArrayLike([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]),
    )

    assert path.read_text(encoding="utf-8") == (
        "x\ty\tz\n"
        "10\t1\t0.1\n"
        "20\t1\t0.2\n"
        "10\t2\t0.3\n"
        "20\t2\t0.4\n"
        "10\t3\t0.5\n"
        "20\t3\t0.6\n"
    )


def test_export_table_rejects_mismatched_vector_lengths(tmp_path: Path) -> None:
    path = tmp_path / "bad.tsv"

    with pytest.raises(ValueError, match="same length"):
        export_table(path, x=[0, 1], y=[0.0])


def test_export_table_rejects_bad_grid_shape(tmp_path: Path) -> None:
    path = tmp_path / "bad.tsv"

    with pytest.raises(ValueError, match="x column length"):
        export_table(path, x=[0, 1, 2], y=[0, 1], z=[[1, 2], [3, 4]])
