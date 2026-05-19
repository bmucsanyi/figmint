"""Tests for post-plot layout helpers."""

import math
from typing import Any

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.legend import Legend
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Bbox

from figmint import finish, style


def canvas_renderer(canvas: Any) -> RendererBase:
    return canvas.get_renderer()


def legend_box_axes(axis: Axes, legend: Legend) -> Bbox:
    axis.figure.canvas.draw()
    renderer = canvas_renderer(axis.figure.canvas)

    return legend.get_window_extent(renderer).transformed(axis.transAxes.inverted())


def frame_inset_axes(axis: Axes, legend: Legend) -> tuple[float, float]:
    axis.figure.canvas.draw()
    renderer = canvas_renderer(axis.figure.canvas)
    axis_box = axis.get_window_extent(renderer)
    inset = 0.5 * legend.get_frame().get_linewidth() * axis.figure.dpi / 72.0

    return inset / axis_box.width, inset / axis_box.height


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
        axis.legend(loc="upper right")

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, _ = frame_inset_axes(axis, legend)

        assert box.x1 == pytest.approx(1.0 - inset_x)
        assert box.y1 == pytest.approx(0.8)

        plt.close(figure)


def test_finish_center_right_snaps_right_edge_and_preserves_center() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")
        initial_legend = axis.legend(loc="center right")
        initial_box = legend_box_axes(axis, initial_legend)
        initial_center_y = 0.5 * (initial_box.y0 + initial_box.y1)

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, _ = frame_inset_axes(axis, legend)

        assert box.x1 == pytest.approx(1.0 - inset_x)
        assert 0.5 * (box.y0 + box.y1) == pytest.approx(initial_center_y)

        plt.close(figure)


def test_finish_keeps_spines_above_no_edge_legend() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")
        axis.legend(loc="upper left")

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None

        for spine in axis.spines.values():
            assert spine.get_zorder() > legend.get_zorder()

        plt.close(figure)


def test_finish_top_center_snaps_top_edge_and_preserves_center() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")
        initial_legend = axis.legend(loc="upper center")
        initial_box = legend_box_axes(axis, initial_legend)
        initial_center_x = 0.5 * (initial_box.x0 + initial_box.x1)

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        _, inset_y = frame_inset_axes(axis, legend)

        assert 0.5 * (box.x0 + box.x1) == pytest.approx(initial_center_x)
        assert box.y1 == pytest.approx(1.0 - inset_y)

        plt.close(figure)


def test_finish_center_center_preserves_both_centers() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")
        initial_legend = axis.legend(loc="center")
        initial_box = legend_box_axes(axis, initial_legend)
        initial_center_x = 0.5 * (initial_box.x0 + initial_box.x1)
        initial_center_y = 0.5 * (initial_box.y0 + initial_box.y1)

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)

        assert 0.5 * (box.x0 + box.x1) == pytest.approx(initial_center_x)
        assert 0.5 * (box.y0 + box.y1) == pytest.approx(initial_center_y)

        plt.close(figure)


def test_finish_snap_survives_constrained_layout_reflow() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axes = plt.subplots(1, 2)
        axis = axes[0]
        axis.set_xlim(0.0, 4.0)
        axis.set_ylim(0.0, 5.0)
        axis.set_xticks([0.0, 1.0, 2.0, 3.0, 4.0])
        axis.set_yticks([0.0, 1.0, 2.0, 3.0, 4.0])
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")
        axis.legend(loc="upper right")

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, _ = frame_inset_axes(axis, legend)

        assert box.x1 == pytest.approx(1.0 - inset_x)
        assert box.y1 == pytest.approx(0.8)

        plt.close(figure)


def test_finish_optimizes_fixed_location_column_count() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        xs = [float(index) / 100.0 for index in range(101)]
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.5, 1.0])
        axis.set_yticks([0.0, 0.5, 1.0])

        for index in range(4):
            ys = [0.20 + 0.12 * float(index) + 0.02 * x for x in xs]
            axis.plot(xs, ys, label=f"run {index + 1}")

        initial_legend = axis.legend(loc="lower right")
        initial_box = legend_box_axes(axis, initial_legend)

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, inset_y = frame_inset_axes(axis, legend)

        assert vars(legend)["_ncols"] == 2
        assert box.height < initial_box.height
        assert box.x1 == pytest.approx(1.0 - inset_x)
        assert box.y0 == pytest.approx(inset_y)

        plt.close(figure)


def test_finish_best_uses_data_margin_for_high_left_data() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        xs = [float(index) / 100.0 for index in range(101)]
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.5, 1.0])
        axis.set_yticks([0.0, 0.5, 1.0])

        for index in range(4):
            ys = [0.92 - 0.45 * x + 0.02 * float(index) for x in xs]
            axis.plot(xs, ys, label=f"run {index + 1}")

        axis.legend(loc="best")
        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, inset_y = frame_inset_axes(axis, legend)

        assert box.x0 == pytest.approx(inset_x)
        assert box.y0 == pytest.approx(inset_y)

        plt.close(figure)


def test_finish_best_uses_data_margin_for_low_left_data() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        xs = [float(index) / 100.0 for index in range(101)]
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.5, 1.0])
        axis.set_yticks([0.0, 0.5, 1.0])

        for index in range(4):
            ys = [0.12 + 0.45 * x + 0.02 * float(index) for x in xs]
            axis.plot(xs, ys, label=f"run {index + 1}")

        axis.legend(loc="best")
        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, inset_y = frame_inset_axes(axis, legend)

        assert box.x0 == pytest.approx(inset_x)
        assert box.y1 == pytest.approx(1.0 - inset_y)

        plt.close(figure)


def test_finish_best_uses_local_clearance_when_global_margin_ties() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axes = plt.subplots(1, 2, figsize=(8.0, 4.0))
        xs = [float(index) / 100.0 for index in range(101)]

        for axis in axes:
            axis.set_xlim(0.0, 1.0)
            axis.set_ylim(0.0, 1.0)
            axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
            axis.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])

        for index in range(4):
            ys = [0.14 + 0.45 * x + 0.02 * float(index) for x in xs]
            axes[0].plot(xs, ys, label=f"run {index + 1}")

        axes[0].legend(loc="best")
        finish(axes[0])
        low_left_legend = axes[0].get_legend()
        assert low_left_legend is not None
        low_left_box = legend_box_axes(axes[0], low_left_legend)
        low_left_inset_x, low_left_inset_y = frame_inset_axes(axes[0], low_left_legend)

        assert low_left_box.x0 == pytest.approx(low_left_inset_x)
        assert low_left_box.y1 == pytest.approx(1.0 - low_left_inset_y)

        for index in range(4):
            ys = [0.37 + 0.45 * x + 0.02 * float(index) for x in xs]
            axes[1].plot(xs, ys, label=f"run {index + 1}")

        axes[1].legend(loc="best")
        finish(axes[1])
        high_right_legend = axes[1].get_legend()
        assert high_right_legend is not None
        high_right_box = legend_box_axes(axes[1], high_right_legend)
        high_right_inset_x, high_right_inset_y = frame_inset_axes(
            axes[1], high_right_legend
        )

        assert high_right_box.x1 == pytest.approx(1.0 - high_right_inset_x)
        assert high_right_box.y0 == pytest.approx(high_right_inset_y)

        figure.set_dpi(300.0)
        low_left_box = legend_box_axes(axes[0], low_left_legend)
        high_right_box = legend_box_axes(axes[1], high_right_legend)
        low_left_inset_x, low_left_inset_y = frame_inset_axes(axes[0], low_left_legend)
        high_right_inset_x, high_right_inset_y = frame_inset_axes(
            axes[1], high_right_legend
        )

        assert low_left_box.x0 == pytest.approx(low_left_inset_x, abs=2.0e-6)
        assert low_left_box.y1 == pytest.approx(1.0 - low_left_inset_y, abs=2.0e-6)
        assert high_right_box.x1 == pytest.approx(1.0 - high_right_inset_x, abs=2.0e-6)
        assert high_right_box.y0 == pytest.approx(high_right_inset_y, abs=2.0e-6)

        plt.close(figure)


def test_finish_best_prefers_local_clearance_before_growth_margin() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axes = plt.subplots(2, 3, figsize=(12.0, 7.0), dpi=200.0)
        axis = axes[1, 0]
        xs = [float(index) / 179.0 for index in range(180)]
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        axis.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])

        for index in range(4):
            ys = [
                0.35
                + 0.1 * float(index)
                + 0.04 * math.sin(5.0 * math.pi * x + float(index))
                for x in xs
            ]
            axis.plot(xs, ys, label=f"run {index + 1}")

        axis.text(
            0.14,
            0.80,
            "note",
            bbox={"facecolor": "white", "edgecolor": "black", "linewidth": 0.5},
        )
        axis.add_patch(Rectangle((0.62, 0.18), 0.18, 0.16, fill=False, linewidth=0.8))
        axis.add_patch(Circle((0.72, 0.72), 0.07, fill=False, linewidth=0.8))
        axis.legend(loc="best")

        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)
        inset_x, inset_y = frame_inset_axes(axis, legend)

        assert vars(legend)["_ncols"] == 2
        assert box.x0 == pytest.approx(inset_x)
        assert box.y0 == pytest.approx(inset_y)

        plt.close(figure)


def test_finish_best_uses_display_clearance_for_center_gap() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots(figsize=(12.0, 10.0), dpi=200.0)
        centers = ((0.20, 0.80), (0.80, 0.20), (0.80, 0.80), (0.20, 0.20))
        offsets = (-0.035, -0.015, 0.015, 0.035)
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        axis.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])

        for index, center in enumerate(centers):
            xs = [center[0] + x_offset for x_offset in offsets for _ in offsets]
            ys = [center[1] + y_offset for _ in offsets for y_offset in offsets]
            axis.scatter(xs, ys, s=16.0, label=f"group {index + 1}")

        axis.legend(loc="best")
        finish(axis)
        legend = axis.get_legend()
        assert legend is not None
        box = legend_box_axes(axis, legend)

        assert vars(legend)["_ncols"] == 2
        assert 0.5 * (box.x0 + box.x1) == pytest.approx(0.5)
        assert 0.5 * (box.y0 + box.y1) == pytest.approx(0.5)

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
