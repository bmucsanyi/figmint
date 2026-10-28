"""Tests for legend creation and the placement rule shared with PGFPlots."""

import csv
import math
from collections.abc import Callable
from operator import itemgetter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.patches import Circle, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Bbox

from figmint import legend, style
from figmint._legend import (
    CELL_PT,
    SCALE_UNIT,
    UNBOUNDED,
    _Anchor,
    _clearance,
    _Grid,
    _Ink,
    _legend_loc,
    _margin,
    _mark_interiors,
    _mark_segments,
    _occupancy_grid,
)

FIXTURES = Path(__file__).parent / "fixtures" / "legend"
CM_PER_INCH = 2.54
PGF_ANCHORS = {
    1: "north east",
    2: "north west",
    3: "south west",
    4: "south east",
    5: "east",
    6: "west",
    7: "east",
    8: "south",
    9: "north",
    10: "center",
}
MATPLOTLIB_LOCS = {
    "best": "best",
    "north east": "upper right",
    "north west": "upper left",
    "south west": "lower left",
    "south east": "lower right",
    "east": "right",
    "west": "center left",
    "south": "lower center",
    "north": "upper center",
    "center": "center",
}


def grid_from(occupied: np.ndarray) -> _Grid:
    table = np.zeros((occupied.shape[0] + 1, occupied.shape[1] + 1), dtype=np.int64)
    table[1:, 1:] = occupied.cumsum(axis=0).cumsum(axis=1)

    return _Grid(
        width=occupied.shape[1] * CELL_PT,
        height=occupied.shape[0] * CELL_PT,
        table=table,
        ink_cells=np.argwhere(occupied)[:, ::-1],
    )


def occupied_cells(occupied: np.ndarray) -> set[tuple[int, int]]:
    return {(int(column), int(row)) for row, column in np.argwhere(occupied)}


def test_segments_occupy_cells_of_half_cell_samples() -> None:
    occupied = np.zeros((5, 5), dtype=bool)
    segments = np.array([[1.0, 5.0, 9.0, 5.0], [0.5, 0.5, 9.5, 9.5]])

    _mark_segments(occupied, segments, width=10.0, height=10.0)

    horizontal = {(column, 2) for column in range(5)}
    diagonal = {(index, index) for index in range(5)}
    assert occupied_cells(occupied) == horizontal | diagonal


def test_segments_are_clipped_to_the_axes() -> None:
    occupied = np.zeros((5, 5), dtype=bool)
    segments = np.array([[-1.0e9, 3.0, 1.0e9, 3.0], [20.0, 0.0, 30.0, 10.0]])

    _mark_segments(occupied, segments, width=10.0, height=10.0)

    assert occupied_cells(occupied) == {(column, 1) for column in range(5)}


def test_filled_path_occupies_its_interior_and_boundary() -> None:
    square = np.array([[0.5, 0.5], [9.5, 0.5], [9.5, 9.5], [0.5, 9.5]])
    stroked = _Ink()
    stroked.add_outline([(square, True)], np.zeros((1, 2)), stroke=True, fill=False)
    filled = _Ink()
    filled.add_outline([(square, False)], np.zeros((1, 2)), stroke=False, fill=True)

    ring = _occupancy_grid(stroked, width=10.0, height=10.0)
    disc = _occupancy_grid(filled, width=10.0, height=10.0)

    assert ring.count(0, 4, 0, 4) == 16
    assert ring.count(1, 3, 1, 3) == 0
    assert disc.count(0, 4, 0, 4) == 25


def test_interiors_match_matplotlib_point_in_polygon() -> None:
    triangle = np.array([[0.3, 0.3], [19.7, 0.4], [0.4, 15.6]])
    edges = np.concatenate((triangle, np.roll(triangle, -1, axis=0)), axis=1)
    occupied = np.zeros((10, 12), dtype=bool)

    _mark_interiors(occupied, edges, np.zeros(len(edges), dtype=np.int64))

    rows, columns = np.mgrid[0:10, 0:12]
    centers = np.stack(((columns + 0.5) * CELL_PT, (rows + 0.5) * CELL_PT), axis=-1)
    inside = MplPath(triangle).contains_points(centers.reshape(-1, 2)).reshape(10, 12)
    assert np.array_equal(occupied, inside)


def test_summed_area_counts_match_naive_counts() -> None:
    generator = np.random.default_rng(7)
    occupied = generator.random((23, 31)) < 0.3
    grid = grid_from(occupied)

    for _ in range(200):
        first_column, last_column = np.sort(generator.integers(0, 31, size=2))
        first_row, last_row = np.sort(generator.integers(0, 23, size=2))
        expected = occupied[
            first_row : last_row + 1, first_column : last_column + 1
        ].sum()

        assert grid.count(first_column, last_column, first_row, last_row) == expected


def test_clearance_is_squared_distance_between_nearest_cells() -> None:
    occupied = np.zeros((10, 20), dtype=bool)
    occupied[3, 10] = True
    occupied[9, 19] = True

    assert _clearance(grid=grid_from(occupied), cells=(0, 2, 0, 1)) == 8**2 + 2**2
    assert _clearance(
        grid=grid_from(np.zeros((4, 4), dtype=bool)), cells=(0, 1, 0, 1)
    ) == (UNBOUNDED)


def test_margin_is_largest_free_growth_about_the_anchor() -> None:
    occupied = np.zeros((20, 20), dtype=bool)
    occupied[0, 9] = True
    lower_left = _Anchor(loc=3, rank=3, x=0, y=0, complexity=0)

    margin = _margin(
        grid=grid_from(occupied), anchor=lower_left, box=(0.0, 0.0, 10.0, 4.0)
    )

    assert margin == int(18.0 * SCALE_UNIT / 10.0)
    assert (
        _margin(
            grid=grid_from(np.zeros((20, 20), dtype=bool)),
            anchor=lower_left,
            box=(0.0, 0.0, 10.0, 4.0),
        )
        == UNBOUNDED
    )


def legend_box_axes(axis: Axes, placed: Legend) -> Bbox:
    axis.figure.canvas.draw()

    return placed.get_window_extent().transformed(axis.transAxes.inverted())


def frame_inset_axes(axis: Axes, placed: Legend) -> tuple[float, float]:
    axis.figure.canvas.draw()
    axis_box = axis.get_window_extent()
    inset = 0.5 * placed.get_frame().get_linewidth() * axis.figure.dpi / 72.0

    return inset / axis_box.width, inset / axis_box.height


def assert_at_anchor(axis: Axes, placed: Legend, *, x_side: int, y_side: int) -> None:
    """Check that a legend sits flush at an anchor given in halves of the axes size.

    Side 0 is the left or bottom edge, 1 the middle, and 2 the right or top edge.
    At an edge, a legend with a frame stays inside by half its frame line width.
    """
    box = legend_box_axes(axis, placed)
    inset_x, inset_y = frame_inset_axes(axis, placed)

    for low, high, inset, side in (
        (box.x0, box.x1, inset_x, x_side),
        (box.y0, box.y1, inset_y, y_side),
    ):
        position = (low, 0.5 * (low + high), high)[side]

        assert position == pytest.approx((inset, 0.5, 1.0 - inset)[side])


def unit_axes(ticks: list[float]) -> tuple[Figure, Axes]:
    figure, axis = plt.subplots()
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.set_xticks(ticks)
    axis.set_yticks(ticks)

    return figure, axis


def fixture_cases() -> list[dict[str, str]]:
    with (FIXTURES / "cases.tsv").open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_series(case: str, series: str) -> tuple[list[float], list[float]]:
    with (FIXTURES / case / f"{series}.tsv").open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    return [float(row["x"]) for row in rows], [float(row["y"]) for row in rows]


@pytest.mark.parametrize("case", fixture_cases(), ids=itemgetter("case"))
def test_legend_matches_shared_fixture(
    case: dict[str, str], legend_columns: Callable[[Axes], int]
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure = plt.figure(
            figsize=(10.0 / CM_PER_INCH, 7.0 / CM_PER_INCH), layout="none"
        )
        axis = figure.add_axes((0.1, 1.0 / 7.0, 0.8, 5.0 / 7.0))
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, 0.5, 1.0])
        axis.set_yticks([0.0, 0.5, 1.0])

        for series in case["series"].split(","):
            xs, ys = read_series(case["case"], series)

            if case["kind"] == "polygon":
                axis.fill(xs, ys, label=series, linewidth=0.0)
            elif case["kind"] == "bar":
                axis.bar(xs, ys, width=0.08, label=series, linewidth=0.0)
            else:
                axis.plot(xs, ys, label=series)

        placed = legend(axis, loc=MATPLOTLIB_LOCS[case["location"]])
        loc = _legend_loc(placed)

        assert isinstance(loc, int)
        assert PGF_ANCHORS[loc] == case["anchor"]
        assert legend_columns(axis) == int(case["columns"])

        plt.close(figure)


@pytest.mark.parametrize(
    ("loc", "x_side", "y_side"),
    [
        ("upper right", 2, 2),
        ("lower right", 2, 0),
        ("upper left", 0, 2),
        ("center right", 2, 1),
        ("upper center", 1, 2),
        ("center", 1, 1),
    ],
)
def test_legend_sits_flush_at_a_fixed_anchor(
    loc: str, x_side: int, y_side: int
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = unit_axes([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")

        assert_at_anchor(axis, legend(axis, loc=loc), x_side=x_side, y_side=y_side)

        plt.close(figure)


def test_legend_corner_survives_constrained_layout() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axes = plt.subplots(1, 2)
        axis = axes[0]
        axis.set_xlim(0.0, 4.0)
        axis.set_ylim(0.0, 5.0)
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")

        placed = legend(axis, loc="upper right")
        box = legend_box_axes(axis, placed)
        inset_x, inset_y = frame_inset_axes(axis, placed)

        assert box.x1 == pytest.approx(1.0 - inset_x)
        assert box.y1 == pytest.approx(1.0 - inset_y)

        plt.close(figure)


def test_legend_keeps_spines_above_a_legend_without_edge() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")

        placed = legend(axis, loc="upper left")

        for spine in axis.spines.values():
            assert spine.get_zorder() > placed.get_zorder()

        plt.close(figure)


def test_legend_measures_candidates_with_the_given_options(
    legend_columns: Callable[[Axes], int],
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure = plt.figure(figsize=(3.0, 2.0), layout="none")
        axis = figure.add_axes((0.25, 0.3, 1.25 / 3.0, 0.75 / 2.0))
        axis.plot([], [], label="a")
        axis.plot([], [], label="b")

        legend(axis, loc="best")
        compact_columns = legend_columns(axis)
        placed = legend(axis, loc="best", labelspacing=5.0)
        box = legend_box_axes(axis, placed)

        assert compact_columns == 1
        assert legend_columns(axis) == 2
        assert box.y0 >= 0.0
        assert box.y1 <= 1.0

        plt.close(figure)


def test_legend_keeps_the_given_options() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()
        axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")

        placed = legend(
            axis,
            loc="best",
            fontsize=6.0,
            handlelength=0.5,
            labelcolor="red",
            title="runs",
        )

        assert [text.get_fontsize() for text in placed.get_texts()] == [6.0]
        assert placed.handlelength == pytest.approx(0.5)
        assert [to_hex(text.get_color()) for text in placed.get_texts()] == ["#ff0000"]
        assert placed.get_title().get_text() == "runs"

        plt.close(figure)


@pytest.mark.parametrize(
    "option",
    [{"ncols": 2}, {"bbox_to_anchor": (1.0, 1.0)}, {"borderaxespad": 1.0}],
)
def test_legend_rejects_options_that_set_the_placement(
    option: dict[str, object],
) -> None:
    figure, axis = plt.subplots()
    axis.plot([0.0, 1.0], [0.0, 1.0], label="baseline")

    with pytest.raises(ValueError, match="does not take"):
        legend(axis, **option)

    plt.close(figure)


@pytest.mark.filterwarnings("ignore:No artists with labels found")
def test_legend_rejects_axes_without_labeled_artists() -> None:
    figure, axis = plt.subplots()
    axis.plot([0.0, 1.0], [0.0, 1.0])

    with pytest.raises(ValueError, match="no labeled artists"):
        legend(axis)

    assert axis.get_legend() is None

    plt.close(figure)


def test_legend_rejects_a_legend_larger_than_the_axes() -> None:
    figure, axis = plt.subplots(figsize=(1.0, 0.5))
    axis.plot([0.0, 1.0], [0.0, 1.0], label="a label far wider than the axes")

    with pytest.raises(ValueError, match="No legend placement fits inside the axes"):
        legend(axis, loc="best")

    plt.close(figure)


@pytest.mark.parametrize("entry_count", [1, 6])
def test_legend_draws_once_for_any_entry_count(entry_count: int) -> None:
    figure, axis = plt.subplots()
    draws = []
    figure.canvas.mpl_connect("draw_event", draws.append)

    for index in range(entry_count):
        axis.plot([0.0, 1.0], [index, index + 1.0], label=f"run {index}")

    legend(axis, loc="best")

    assert len(draws) == 1

    plt.close(figure)


def test_legend_snaps_explicit_position_to_nearest_grid_intersection() -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = unit_axes([0.0, 0.25, 0.5, 0.75, 1.0])
        axis.plot([0.0, 1.0], [0.0, 0.1], label="baseline")

        placed = legend(axis, loc=(0.33, 0.47))

        assert _legend_loc(placed) == pytest.approx((0.25, 0.5))

        plt.close(figure)


@pytest.mark.parametrize("kind", ["image", "mesh"])
def test_legend_treats_raster_content_as_ink(kind: str) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots(layout="none")
        values = np.arange(4.0).reshape(2, 2)

        if kind == "image":
            axis.imshow(values, extent=(0.0, 1.0, 0.5, 1.0), aspect="auto")
        else:
            axis.pcolormesh([0.0, 0.5, 1.0], [0.5, 0.75, 1.0], values)

        axis.plot([0.0, 1.0], [0.0, 0.0], label="floor")
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)

        placed = legend(axis, loc="best")
        loc = _legend_loc(placed)

        assert isinstance(loc, int)
        assert PGF_ANCHORS[loc] == "south west"

        plt.close(figure)


def test_legend_at_a_fixed_anchor_chooses_the_column_count(
    legend_columns: Callable[[Axes], int],
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = unit_axes([0.0, 0.5, 1.0])
        xs = [float(index) / 100.0 for index in range(101)]

        for index in range(4):
            ys = [0.20 + 0.12 * float(index) + 0.02 * x for x in xs]
            axis.plot(xs, ys, label=f"run {index + 1}")

        single_column = axis.legend(loc="lower right")
        single_column_box = legend_box_axes(axis, single_column)
        placed = legend(axis, loc="lower right")
        box = legend_box_axes(axis, placed)
        inset_x, inset_y = frame_inset_axes(axis, placed)

        assert legend_columns(axis) == 2
        assert box.height < single_column_box.height
        assert box.x1 == pytest.approx(1.0 - inset_x)
        assert box.y0 == pytest.approx(inset_y)

        plt.close(figure)


def test_legend_avoids_empty_legend_cells(
    legend_columns: Callable[[Axes], int],
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = unit_axes([0.0, 0.5, 1.0])
        xs = [float(index) / 100.0 for index in range(101)]

        for index in range(3):
            ys = [0.55 + 0.03 * float(index) + 0.02 * x for x in xs]
            axis.plot(xs, ys, label=f"run {index + 1}")

        legend(axis, loc="best")

        assert legend_columns(axis) in {1, 3}

        plt.close(figure)


@pytest.mark.parametrize(
    ("offset", "slope", "x_side", "y_side"),
    [(0.92, -0.45, 0, 0), (0.12, 0.45, 0, 2)],
)
def test_legend_best_goes_to_the_free_corner(
    offset: float, slope: float, x_side: int, y_side: int
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = unit_axes([0.0, 0.5, 1.0])
        xs = [float(index) / 100.0 for index in range(101)]

        for index in range(4):
            ys = [offset + slope * x + 0.02 * float(index) for x in xs]
            axis.plot(xs, ys, label=f"run {index + 1}")

        assert_at_anchor(axis, legend(axis, loc="best"), x_side=x_side, y_side=y_side)

        plt.close(figure)


def test_legend_best_uses_local_clearance_when_global_margin_ties() -> None:
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

        low_left = legend(axes[0], loc="best")
        low_left_box = legend_box_axes(axes[0], low_left)
        low_left_inset_x, low_left_inset_y = frame_inset_axes(axes[0], low_left)

        assert low_left_box.x0 == pytest.approx(low_left_inset_x)
        assert low_left_box.y1 == pytest.approx(1.0 - low_left_inset_y)

        for index in range(4):
            ys = [0.37 + 0.45 * x + 0.02 * float(index) for x in xs]
            axes[1].plot(xs, ys, label=f"run {index + 1}")

        high_right = legend(axes[1], loc="best")
        high_right_box = legend_box_axes(axes[1], high_right)
        high_right_inset_x, high_right_inset_y = frame_inset_axes(axes[1], high_right)

        assert high_right_box.x1 == pytest.approx(1.0 - high_right_inset_x)
        assert high_right_box.y0 == pytest.approx(high_right_inset_y)

        figure.set_dpi(300.0)
        low_left_box = legend_box_axes(axes[0], low_left)
        high_right_box = legend_box_axes(axes[1], high_right)
        low_left_inset_x, low_left_inset_y = frame_inset_axes(axes[0], low_left)
        high_right_inset_x, high_right_inset_y = frame_inset_axes(axes[1], high_right)

        assert low_left_box.x0 == pytest.approx(low_left_inset_x, abs=2.0e-6)
        assert low_left_box.y1 == pytest.approx(1.0 - low_left_inset_y, abs=2.0e-6)
        assert high_right_box.x1 == pytest.approx(1.0 - high_right_inset_x, abs=2.0e-6)
        assert high_right_box.y0 == pytest.approx(high_right_inset_y, abs=2.0e-6)

        plt.close(figure)


def test_legend_best_prefers_local_clearance_before_growth_margin(
    legend_columns: Callable[[Axes], int],
) -> None:
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

        placed = legend(axis, loc="best")
        box = legend_box_axes(axis, placed)
        inset_x, inset_y = frame_inset_axes(axis, placed)

        assert legend_columns(axis) == 2
        assert box.x0 == pytest.approx(inset_x)
        assert box.y0 == pytest.approx(inset_y)

        plt.close(figure)


def test_legend_best_uses_display_clearance_for_center_gap(
    legend_columns: Callable[[Axes], int],
) -> None:
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

        placed = legend(axis, loc="best")
        box = legend_box_axes(axis, placed)

        assert legend_columns(axis) == 2
        assert 0.5 * (box.x0 + box.x1) == pytest.approx(0.5)
        assert 0.5 * (box.y0 + box.y1) == pytest.approx(0.5)

        plt.close(figure)


def test_legend_best_chooses_the_column_count(
    legend_columns: Callable[[Axes], int],
) -> None:
    with plt.rc_context(style("normal", venue="icml")):
        figure, axis = plt.subplots()

        for index in range(4):
            axis.plot([0.0, 1.0], [float(index), float(index)], label=f"curve {index}")

        single_column = axis.legend(loc="best")
        single_column_box = legend_box_axes(axis, single_column)
        placed = legend(axis, loc="best")
        box = legend_box_axes(axis, placed)

        assert legend_columns(axis) == 2
        assert box.height < single_column_box.height
        assert box.width > single_column_box.width

        plt.close(figure)
