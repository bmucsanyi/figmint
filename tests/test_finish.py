"""Tests for post-plot layout helpers."""

from typing import Any

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox

from figmint import finish, style


def canvas_renderer(canvas: Any) -> RendererBase:
    return canvas.get_renderer()


def legend_box_axes(axis: Axes, legend: Legend) -> Bbox:
    axis.figure.canvas.draw()
    renderer = canvas_renderer(axis.figure.canvas)

    return legend.get_window_extent(renderer).transformed(axis.transAxes.inverted())


def test_finish_returns_axis_without_legend() -> None:
    figure, axis = plt.subplots()

    assert finish(axis) is axis

    plt.close(figure)


def test_finish_snaps_fixed_legend_location_to_major_grid() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.set_xlim(0.0, 4.0)
        axis.set_ylim(0.0, 5.0)
        axis.set_xticks([0.0, 1.0, 2.0, 3.0, 4.0])
        axis.set_yticks([0.0, 1.0, 2.0, 3.0, 4.0])
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")
        legend = axis.legend(loc="upper right")

        finish(axis)
        box = legend_box_axes(axis, legend)

        assert box.x1 == pytest.approx(1.0)
        assert box.y1 == pytest.approx(0.8)

        plt.close(figure)


def test_finish_optimizes_best_legend_column_count() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()

        for index in range(4):
            axis.plot([0.0, 1.0], [float(index), float(index)], label=f"curve {index}")

        legend = axis.legend(loc="best")
        initial_box = legend_box_axes(axis, legend)

        finish(axis)
        finished = axis.get_legend()
        assert finished is not None

        finished_box = legend_box_axes(axis, finished)

        assert vars(finished)["_ncols"] == 2
        assert finished_box.height < initial_box.height
        assert finished_box.width > initial_box.width

        plt.close(figure)
