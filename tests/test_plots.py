"""Tests for the plot functions of the look."""

from collections.abc import Sequence

import matplotlib as mpl
import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgb, to_rgba
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch

from figmint import (
    area,
    bar,
    boxplot,
    colorbar,
    hbar,
    heatmap,
    interval,
    scatter,
    style,
)
from figmint._colors import COLOR_THEMES, Theme
from figmint._ticks import NumberFormatter

POINTS_PER_INCH = 72.0
FIGURE_SIZE = (3.25, 2.0)


def new_figure() -> tuple[Figure, FigureCanvasAgg]:
    figure = Figure()
    canvas = FigureCanvasAgg(figure)

    return figure, canvas


def tint(color: str, background: str, amount: float) -> tuple[float, ...]:
    foreground = np.asarray(to_rgb(color))
    behind = np.asarray(to_rgb(background))

    return tuple(amount * foreground + (1.0 - amount) * behind)


def points(extents: Sequence[float], figure: Figure) -> list[float]:
    return [float(value) * POINTS_PER_INCH / figure.dpi for value in extents]


@pytest.mark.parametrize("theme", ["normal", "frappe"])
def test_bars_are_tinted_and_outlined_in_their_color(theme: Theme) -> None:
    with mpl.rc_context(style(theme, figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, _ = new_figure()
        axes = figure.subplots()
        first = bar(axes, [1, 2], [0.5, 0.7])
        second = bar(axes, [1, 2], [0.4, 0.6])

    colors = COLOR_THEMES[theme]

    for container, color in ((first, colors["cycle"][0]), (second, colors["cycle"][1])):
        for patch in container.patches:
            assert to_rgba(patch.get_facecolor())[:3] == pytest.approx(
                tint(color, colors["background"], 0.3)
            )
            assert to_rgba(patch.get_edgecolor())[:3] == pytest.approx(to_rgb(color))


def test_grouped_bars_stand_side_by_side_around_the_position() -> None:
    with mpl.rc_context(style("normal", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, _ = new_figure()
        axes = figure.subplots()
        containers = [bar(axes, [2.0], [1.0], group=(index, 3)) for index in range(3)]

    centers = [
        container.patches[0].get_x() + container.patches[0].get_width() / 2.0
        for container in containers
    ]
    width = containers[0].patches[0].get_width()

    assert width == pytest.approx(min(0.22, 0.8 / 3))
    assert centers == pytest.approx([2.0 - width, 2.0, 2.0 + width])


def test_a_single_bar_has_the_single_width() -> None:
    with mpl.rc_context(style("normal", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, _ = new_figure()
        axes = figure.subplots()
        container = bar(axes, [1.0], [1.0])

    assert container.patches[0].get_width() == pytest.approx(0.4125)
    assert container.patches[0].get_x() == pytest.approx(1.0 - 0.4125 / 2.0)


def test_bar_rejects_an_index_outside_the_group() -> None:
    figure, _ = new_figure()
    axes = figure.subplots()

    with pytest.raises(ValueError, match="0 <= index < count"):
        bar(axes, [1.0], [1.0], group=(3, 3))


def test_horizontal_bars_put_the_grid_along_the_value_axis() -> None:
    with mpl.rc_context(style("normal", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, canvas = new_figure()
        axes = figure.subplots()
        hbar(axes, [1, 2], [0.5, 0.7])
        canvas.draw()

    assert axes.xaxis.get_gridlines()[0].get_visible()
    assert not axes.yaxis.get_gridlines()[0].get_visible()


def test_area_and_interval_fill_at_opacity_018_without_an_edge() -> None:
    with mpl.rc_context(style("normal", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, _ = new_figure()
        axes = figure.subplots()
        line = area(axes, [0.0, 1.0], [1.0, 2.0])
        band = interval(axes, [0.0, 1.0], [0.0, 0.5], [1.0, 1.5], color="#ff0000")

    (under,) = axes.collections[:1]

    assert under.get_alpha() == pytest.approx(0.18)
    assert np.asarray(under.get_facecolor())[0, :3] == pytest.approx(
        to_rgb(line.get_color())
    )
    assert np.asarray(under.get_linewidth())[0] == pytest.approx(0.0)
    assert band.get_alpha() == pytest.approx(0.18)
    assert np.asarray(band.get_facecolor())[0, :3] == pytest.approx((1.0, 0.0, 0.0))
    assert np.asarray(band.get_linewidth())[0] == pytest.approx(0.0)


def test_scatter_and_heatmap_switch_the_grid_off() -> None:
    with mpl.rc_context(style("normal", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, canvas = new_figure()
        left, right = figure.subplots(1, 2)
        discs = scatter(left, [0.0, 1.0], [0.0, 1.0])
        image = heatmap(right, [[0.0, 1.0], [2.0, 3.0]], extent=(0.0, 2.0, 0.0, 2.0))
        canvas.draw()

    for axes in (left, right):
        assert not axes.xaxis.get_gridlines()[0].get_visible()
        assert not axes.yaxis.get_gridlines()[0].get_visible()

    assert np.asarray(discs.get_linewidth())[0] == pytest.approx(0.0)
    assert tuple(image.get_extent()) == (0.0, 2.0, 0.0, 2.0)
    assert image.origin == "lower"


def test_colorbar_is_four_points_wide_four_points_from_the_axes_and_inside() -> None:
    with mpl.rc_context(style("normal", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, canvas = new_figure()
        axes = figure.subplots()
        image = heatmap(
            axes, np.linspace(0.0, 1.0, 400).reshape(20, 20), vmin=0.0, vmax=1.0
        )
        bar_ = colorbar(axes, image)
        canvas.draw()

    renderer = canvas.get_renderer()
    axes_box = points(axes.get_window_extent(renderer).extents, figure)
    bar_box = points(bar_.ax.get_window_extent(renderer).extents, figure)
    labels = [
        points(label.get_window_extent(renderer).extents, figure)
        for label in bar_.ax.get_yticklabels()
    ]

    assert bar_box[2] - bar_box[0] == pytest.approx(4.0, abs=0.01)
    assert bar_box[0] - axes_box[2] == pytest.approx(4.0, abs=0.01)
    assert bar_box[1] == pytest.approx(axes_box[1], abs=0.01)
    assert bar_box[3] == pytest.approx(axes_box[3], abs=0.01)
    assert max(label[2] for label in labels) <= FIGURE_SIZE[0] * POINTS_PER_INCH
    assert not bar_.ax.spines["outline"].get_visible()
    assert isinstance(bar_.ax.yaxis.get_major_formatter(), NumberFormatter)


def test_boxes_take_the_colors_of_the_cycle_in_turn() -> None:
    with mpl.rc_context(style("latte", figure_size=FIGURE_SIZE, font_size=9.0)):
        figure, _ = new_figure()
        axes = figure.subplots()
        result = boxplot(axes, [[1.0, 2.0, 3.0, 4.0], [2.0, 3.0, 4.0, 5.0]])

    colors = COLOR_THEMES["latte"]

    for index, box in enumerate(result["boxes"]):
        color = colors["cycle"][index]
        median = result["medians"][index]
        assert isinstance(box, PathPatch)
        assert isinstance(median, Line2D)
        assert to_rgba(box.get_facecolor())[:3] == pytest.approx(
            tint(color, colors["background"], 0.12)
        )
        assert to_rgba(box.get_edgecolor())[:3] == pytest.approx(to_rgb(color))
        assert median.get_color() == color
        assert median.get_linewidth() == pytest.approx(1.0)
        assert result["whiskers"][2 * index].get_linewidth() == pytest.approx(0.5)

    assert result["boxes"][0].get_path().get_extents().width == pytest.approx(0.55)
    assert not result["fliers"]
