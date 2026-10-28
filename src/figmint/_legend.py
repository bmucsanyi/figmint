"""Legend creation and placement.

``legend`` creates an axes legend and places it by the rule that the PGFPlots
backend uses, as specified in ``docs/legend.md``. The legend sits flush at one
of nine anchors of the axes, with the column count that covers the least
plotted ink. Ink is measured on a grid of square cells of ``CELL_PT`` points.
"""

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from math import ceil
from operator import itemgetter
from typing import Any

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.collections import Collection, QuadMesh
from matplotlib.colors import to_rgba
from matplotlib.image import AxesImage
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Patch
from matplotlib.path import Path
from matplotlib.spines import Spine
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox
from matplotlib.typing import ColorType

EPSILON = 1.0e-9
UNIT_ROUND_DIGITS = 12
POINTS_PER_INCH = 72.0
CELL_PT = 2.0
SCALE_UNIT = 256
SIZE_UNIT = 10000
UNBOUNDED = np.iinfo(np.int64).max
NO_LINE_STYLES = frozenset({"None", "none", "", " "})
MEASUREMENT_LOC = 1
PLACEMENT_OPTIONS = frozenset({
    "ncols",
    "ncol",
    "bbox_to_anchor",
    "bbox_transform",
    "borderaxespad",
    "mode",
})


@dataclass(frozen=True)
class _Anchor:
    """A candidate legend anchor.

    ``x`` and ``y`` give the position of the anchor in halves of the axes size:
    0, 1, and 2 are the left (bottom) edge, the middle, and the right (top)
    edge. ``rank`` orders the anchors by preference. ``complexity`` ranks the
    corners and the middles of the top and bottom edges first, the middles of
    the left and right edges next, and the center last.
    """

    loc: int
    rank: int
    x: int
    y: int
    complexity: int


ANCHORS = (
    _Anchor(loc=1, rank=1, x=2, y=2, complexity=0),
    _Anchor(loc=2, rank=2, x=0, y=2, complexity=0),
    _Anchor(loc=3, rank=3, x=0, y=0, complexity=0),
    _Anchor(loc=4, rank=4, x=2, y=0, complexity=0),
    _Anchor(loc=5, rank=5, x=2, y=1, complexity=1),
    _Anchor(loc=6, rank=6, x=0, y=1, complexity=1),
    _Anchor(loc=8, rank=7, x=1, y=0, complexity=0),
    _Anchor(loc=9, rank=8, x=1, y=2, complexity=0),
    _Anchor(loc=10, rank=9, x=1, y=1, complexity=2),
)
ANCHORS_BY_LOC = {anchor.loc: anchor for anchor in ANCHORS} | {
    7: _Anchor(loc=7, rank=5, x=2, y=1, complexity=1),
}


@dataclass(frozen=True)
class _Grid:
    """Occupied cells of an axes of ``width`` by ``height`` points.

    ``table[j, i]`` counts the occupied cells in the columns below ``i`` and the
    rows below ``j``. ``ink_cells`` lists the column and row of every occupied
    cell.
    """

    width: float
    height: float
    table: np.ndarray
    ink_cells: np.ndarray

    @property
    def columns(self) -> int:
        return self.table.shape[1] - 1

    @property
    def rows(self) -> int:
        return self.table.shape[0] - 1

    def count(
        self, first_column: int, last_column: int, first_row: int, last_row: int
    ) -> int:
        """Return the number of occupied cells in the inclusive cell ranges."""
        table = self.table

        return int(
            table[last_row + 1, last_column + 1]
            - table[first_row, last_column + 1]
            - table[last_row + 1, first_column]
            + table[first_row, first_column]
        )

    def box_cells(
        self, left: float, right: float, bottom: float, top: float
    ) -> tuple[int, int, int, int]:
        """Return the cell ranges of a box in points that overlaps the axes."""
        first_column, last_column = _interval_cells(
            low=left, high=right, length=self.width, cells=self.columns
        )
        first_row, last_row = _interval_cells(
            low=bottom, high=top, length=self.height, cells=self.rows
        )

        return first_column, last_column, first_row, last_row

    def box_count(self, left: float, right: float, bottom: float, top: float) -> int:
        """Return the number of occupied cells under a box that overlaps the axes."""
        return self.count(*self.box_cells(left, right, bottom, top))


@dataclass
class _Ink:
    """Plotted ink, in points relative to the lower left corner of the axes.

    ``segments`` holds stroked segments and the boundaries of filled paths as
    rows of (x0, y0, x1, y1). ``fill_edges`` holds the edges of filled paths,
    closed implicitly, and ``fill_groups`` names the path of each edge, so
    that the even-odd rule applies per path. ``rectangles`` holds filled boxes
    as rows of (left, bottom, right, top).
    """

    segments: list[np.ndarray] = field(default_factory=list)
    fill_edges: list[np.ndarray] = field(default_factory=list)
    fill_groups: list[np.ndarray] = field(default_factory=list)
    rectangles: list[np.ndarray] = field(default_factory=list)
    groups: int = 0

    def add_outline(
        self,
        outline: list[tuple[np.ndarray, bool]],
        offsets: np.ndarray,
        *,
        stroke: bool,
        fill: bool,
    ) -> None:
        """Add one outline, in points, at every offset, in points.

        Each placement of the outline is one path for the even-odd rule.
        """
        if not (stroke or fill) or len(offsets) == 0:
            return

        parts = [
            _subpath_edges(points, close=closed or fill) for points, closed in outline
        ]
        edges = np.concatenate(parts) if parts else np.zeros((0, 4))
        placed = (edges[None, :, :] + np.tile(offsets, 2)[:, None, :]).reshape(-1, 4)
        self.segments.append(placed)

        if fill:
            self.fill_edges.append(placed)
            self.fill_groups.append(
                np.repeat(np.arange(len(offsets)) + self.groups, len(edges))
            )
            self.groups += len(offsets)

    def add_rectangle(self, corners: np.ndarray) -> None:
        """Add a filled box given by two opposite corners in points."""
        self.rectangles.append(np.asarray(corners, dtype=float).reshape(4))


def legend(axis: Axes, **options: Any) -> Legend:
    """Create the legend of an axes and place it by the rule in docs/legend.md.

    ``options`` are keyword arguments of ``Axes.legend``, and every candidate
    legend is created with them. ``loc`` selects the candidates. At ``"best"``,
    the legend moves to the anchor and column count that cover the least plotted
    ink. At a location such as ``"upper right"``, it keeps that anchor and gets
    the best column count. At axes coordinates, it moves to the nearest major
    grid intersection that keeps it inside the axes. The figure is drawn once,
    to lay it out before the measurements.

    Returns:
        The placed legend.

    Raises:
        ValueError: If ``options`` set the column count or the position, which
            the rule chooses, or if the axes have no labeled artists.
    """
    fixed = sorted(PLACEMENT_OPTIONS & options.keys())

    if fixed:
        msg = (
            f"legend chooses the column count and position, so it does not take "
            f"{fixed}. Use Axes.legend for a manual layout."
        )
        raise ValueError(msg)

    axis.figure.canvas.draw()
    requested = axis.legend(**options)
    entries = len(requested.get_texts())

    if entries == 0:
        requested.remove()
        msg = "The axes have no labeled artists to put in a legend."
        raise ValueError(msg)

    loc = _legend_loc(requested)

    if isinstance(loc, tuple):
        placed = _snap_to_grid(axis=axis, legend=requested)
    else:
        requested.remove()
        placed = _place_at_anchor(
            axis=axis,
            options={key: value for key, value in options.items() if key != "loc"},
            anchors=ANCHORS if loc == Legend.codes["best"] else (ANCHORS_BY_LOC[loc],),
            entries=entries,
        )

    _raise_spines_above_no_edge_legend(axis=axis, legend=placed)

    return placed


def _legend_loc(legend: Legend) -> int | tuple[float, float]:
    """Return the location code or the axes coordinates of a legend.

    Legend has set_loc but no public getter, so this reads the private property.
    """
    return legend._loc  # noqa: SLF001  # ty: ignore[unresolved-attribute]


def _raise_spines_above_no_edge_legend(*, axis: Axes, legend: Legend) -> None:
    edge_rgba = to_rgba(legend.get_frame().get_edgecolor())

    if edge_rgba[3] > EPSILON:
        return

    zorder = legend.get_zorder() + 1.0

    for spine in axis.spines.values():
        spine.set_zorder(zorder)


def _place_at_anchor(
    *,
    axis: Axes,
    options: dict[str, Any],
    anchors: tuple[_Anchor, ...],
    entries: int,
) -> Legend:
    """Create the legend at the best anchor and column count among the anchors.

    Returns:
        The legend, flush with the axes frame at its anchor.
    """
    anchor, columns = _best_placement(
        axis=axis, options=options, anchors=anchors, entries=entries
    )
    placed = axis.legend(**options, loc=anchor.loc, ncols=columns, borderaxespad=0.0)
    placed.set_in_layout(False)
    inset_x, inset_y = _frame_boundary_inset_axes(axis=axis, legend=placed)
    placed.set_bbox_to_anchor(
        (
            _inset_boundary_anchor(value=anchor.x / 2.0, inset=inset_x),
            _inset_boundary_anchor(value=anchor.y / 2.0, inset=inset_y),
        ),
        transform=axis.transAxes,
    )

    return placed


def _best_placement(
    *,
    axis: Axes,
    options: dict[str, Any],
    anchors: tuple[_Anchor, ...],
    entries: int,
) -> tuple[_Anchor, int]:
    """Return the anchor and column count with the best score.

    Returns:
        The best anchor and its column count.

    Raises:
        ValueError: If the legend does not fit inside the axes at any column
            count.
    """
    points_per_pixel = POINTS_PER_INCH / axis.figure.dpi
    axis_box = axis.get_window_extent()
    grid = _occupancy_grid(
        _axes_ink(axis),
        width=axis_box.width * points_per_pixel,
        height=axis_box.height * points_per_pixel,
    )
    candidates = []

    for columns in range(1, entries + 1):
        measured = axis.legend(**options, loc=MEASUREMENT_LOC, ncols=columns)
        size = measured.get_window_extent()
        measured.remove()

        for anchor in anchors:
            score = _candidate_score(
                grid=grid,
                anchor=anchor,
                columns=columns,
                entry_count=entries,
                width=size.width * points_per_pixel,
                height=size.height * points_per_pixel,
            )

            if score is not None:
                candidates.append((score, anchor, columns))

    if not candidates:
        msg = "No legend placement fits inside the axes."
        raise ValueError(msg)

    _, anchor, columns = min(candidates, key=itemgetter(0))

    return anchor, columns


def _candidate_score(
    *,
    grid: _Grid,
    anchor: _Anchor,
    columns: int,
    entry_count: int,
    width: float,
    height: float,
) -> tuple[int, ...] | None:
    """Return the score of a candidate, smaller is better.

    Returns:
        The score tuple, or None when the legend is larger than the axes.
    """
    if width > grid.width or height > grid.height:
        return None

    left = anchor.x * (grid.width - width) / 2.0
    bottom = anchor.y * (grid.height - height) / 2.0
    cells = grid.box_cells(left, left + width, bottom, bottom + height)
    badness = grid.count(*cells)
    rows = ceil(entry_count / columns)
    clearance = 0
    margin = 0

    if badness == 0:
        clearance = _clearance(grid=grid, cells=cells)
        margin = _margin(
            grid=grid,
            anchor=anchor,
            box=(left, bottom, width, height),
        )

    size = int(SIZE_UNIT * width / grid.width) + int(SIZE_UNIT * height / grid.height)

    return (
        badness,
        columns * rows - entry_count,
        abs(columns - rows),
        -clearance,
        -margin,
        anchor.complexity,
        size,
        anchor.rank,
        columns,
    )


def _clearance(*, grid: _Grid, cells: tuple[int, int, int, int]) -> int:
    """Return the squared distance, in cells, from a free box to the nearest ink.

    The distance runs between the centers of the nearest box cell and ink cell.

    Returns:
        The squared distance, or ``UNBOUNDED`` when no cell holds ink.
    """
    if len(grid.ink_cells) == 0:
        return UNBOUNDED

    first_column, last_column, first_row, last_row = cells
    columns, rows = grid.ink_cells.T
    gap_x = np.maximum(0, np.maximum(columns - last_column, first_column - columns))
    gap_y = np.maximum(0, np.maximum(rows - last_row, first_row - rows))

    return int((gap_x * gap_x + gap_y * gap_y).min())


def _margin(
    *, grid: _Grid, anchor: _Anchor, box: tuple[float, float, float, float]
) -> int:
    """Return the largest growth of a free box about its anchor that stays free.

    Returns:
        The growth factor in units of ``1 / SCALE_UNIT``, or ``UNBOUNDED`` when
        the box can grow to cover the axes without touching ink.
    """
    left, bottom, width, height = box
    extent_left = anchor.x * width / 2.0
    extent_right = width - extent_left
    extent_down = anchor.y * height / 2.0
    extent_up = height - extent_down
    anchor_x = left + extent_left
    anchor_y = bottom + extent_down

    def scaled_count(scale: int) -> int:
        factor = scale / SCALE_UNIT

        return grid.box_count(
            anchor_x - extent_left * factor,
            anchor_x + extent_right * factor,
            anchor_y - extent_down * factor,
            anchor_y + extent_up * factor,
        )

    def cover(distance: float, extent: float) -> int:
        if extent <= 0.0:
            return 0

        return int(distance * SCALE_UNIT / extent) + 1

    high = max(
        SCALE_UNIT,
        cover(anchor_x, extent_left),
        cover(grid.width - anchor_x, extent_right),
        cover(anchor_y, extent_down),
        cover(grid.height - anchor_y, extent_up),
    )

    if scaled_count(high) == 0:
        return UNBOUNDED

    low = SCALE_UNIT

    while high - low > 1:
        middle = (low + high) // 2

        if scaled_count(middle) == 0:
            low = middle
        else:
            high = middle

    return low


def _interval_cells(
    *, low: float, high: float, length: float, cells: int
) -> tuple[int, int]:
    """Return the first and last cell of an interval that overlaps the axes."""
    first = min(cells - 1, int(max(0.0, low) // CELL_PT))
    last = min(cells - 1, max(first, ceil(min(length, high) / CELL_PT) - 1))

    return first, last


def _occupancy_grid(ink: _Ink, *, width: float, height: float) -> _Grid:
    occupied = np.zeros((ceil(height / CELL_PT), ceil(width / CELL_PT)), dtype=bool)
    _mark_segments(occupied, _stack(ink.segments), width=width, height=height)
    _mark_interiors(
        occupied,
        _stack(ink.fill_edges),
        np.concatenate(ink.fill_groups) if ink.fill_groups else np.zeros(0, dtype=int),
    )

    for left, bottom, right, top in _stack(ink.rectangles):
        _mark_rectangle(
            occupied, (left, bottom, right, top), width=width, height=height
        )

    table = np.zeros((occupied.shape[0] + 1, occupied.shape[1] + 1), dtype=np.int64)
    table[1:, 1:] = occupied.cumsum(axis=0).cumsum(axis=1)

    return _Grid(
        width=width,
        height=height,
        table=table,
        ink_cells=np.argwhere(occupied)[:, ::-1].astype(np.int64),
    )


def _stack(parts: list[np.ndarray]) -> np.ndarray:
    if not parts:
        return np.zeros((0, 4))

    return np.concatenate([
        np.asarray(part, dtype=float).reshape(-1, 4) for part in parts
    ])


def _mark_cells(occupied: np.ndarray, x: np.ndarray, y: np.ndarray) -> None:
    """Mark the cells that contain the points (x, y), in points."""
    columns = np.floor(x / CELL_PT).astype(np.int64)
    rows = np.floor(y / CELL_PT).astype(np.int64)
    inside = (
        (columns >= 0)
        & (columns < occupied.shape[1])
        & (rows >= 0)
        & (rows < occupied.shape[0])
    )
    occupied[rows[inside], columns[inside]] = True


def _mark_segments(
    occupied: np.ndarray, segments: np.ndarray, *, width: float, height: float
) -> None:
    """Mark the cells that contain points sampled along each segment.

    Each segment is clipped to the axes and sampled at steps of at most half a
    cell along both axes.
    """
    start = segments[:, :2]
    delta = segments[:, 2:] - start
    enter = np.zeros(len(segments))
    leave = np.ones(len(segments))
    inside = np.ones(len(segments), dtype=bool)

    for axis_index, length in ((0, width), (1, height)):
        for step, room in (
            (-delta[:, axis_index], start[:, axis_index]),
            (delta[:, axis_index], length - start[:, axis_index]),
        ):
            moving = (step < 0.0) | (step > 0.0)
            inside &= moving | (room >= 0.0)
            ratio = np.divide(room, step, out=np.zeros_like(room), where=moving)
            enter = np.where(step < 0.0, np.maximum(enter, ratio), enter)
            leave = np.where(step > 0.0, np.minimum(leave, ratio), leave)

    keep = inside & (enter <= leave)
    first = start[keep] + delta[keep] * enter[keep, None]
    span = delta[keep] * (leave - enter)[keep, None]
    steps = np.maximum(
        1, np.ceil(np.abs(span).max(axis=1, initial=0.0) / (0.5 * CELL_PT))
    ).astype(np.int64)
    owner = np.repeat(np.arange(len(steps)), steps + 1)
    index = np.arange(len(owner)) - np.repeat(
        np.cumsum(steps + 1) - (steps + 1), steps + 1
    )
    points = first[owner] + span[owner] * (index / steps[owner])[:, None]
    _mark_cells(occupied, points[:, 0], points[:, 1])


def _mark_interiors(
    occupied: np.ndarray, edges: np.ndarray, groups: np.ndarray
) -> None:
    """Mark the cells whose centers lie inside a filled path (even-odd rule).

    Every edge crosses the horizontal lines through the cell centers of the
    rows it spans; within each path and row, the cells between consecutive
    pairs of crossings are inside.
    """
    rows, crossings, paths = _row_crossings(edges, groups, row_count=occupied.shape[0])
    run_starts = np.flatnonzero(
        np.r_[True, (paths[1:] != paths[:-1]) | (rows[1:] != rows[:-1])]
    )
    run_lengths = np.diff(np.r_[run_starts, len(crossings)])
    position = np.arange(len(crossings)) - np.repeat(run_starts, run_lengths)
    entering = np.flatnonzero(
        (position % 2 == 0) & (position + 1 < np.repeat(run_lengths, run_lengths))
    )
    _mark_spans(
        occupied,
        rows=rows[entering],
        starts=crossings[entering],
        ends=crossings[entering + 1],
    )


def _row_crossings(
    edges: np.ndarray, groups: np.ndarray, *, row_count: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the crossings of edges with the lines through the row centers.

    An edge crosses the line through the centers of row ``j`` when that line
    lies at or above its lower end and below its upper end.

    Returns:
        The row, the x coordinate, and the path of every crossing, sorted by
        path, then row, then x.
    """
    sloped = edges[:, 1] != edges[:, 3]
    x0, y0, x1, y1 = edges[sloped].T
    first = np.maximum(0, np.ceil(np.minimum(y0, y1) / CELL_PT - 0.5)).astype(np.int64)
    last = np.minimum(
        row_count - 1, np.ceil(np.maximum(y0, y1) / CELL_PT - 0.5).astype(np.int64) - 1
    )
    counts = np.maximum(0, last - first + 1)
    edge = np.repeat(np.arange(len(counts)), counts)
    rows = (
        first[edge]
        + np.arange(len(edge))
        - np.repeat(np.cumsum(counts) - counts, counts)
    )
    crossings = (
        x0[edge]
        + ((rows + 0.5) * CELL_PT - y0[edge]) * (x1 - x0)[edge] / (y1 - y0)[edge]
    )
    paths = groups[sloped][edge]
    order = np.lexsort((crossings, rows, paths))

    return rows[order], crossings[order], paths[order]


def _mark_spans(
    occupied: np.ndarray, *, rows: np.ndarray, starts: np.ndarray, ends: np.ndarray
) -> None:
    """Mark the cells of each row whose centers lie in [start, end)."""
    columns_total = occupied.shape[1]
    first = np.maximum(0, np.ceil(starts / CELL_PT - 0.5)).astype(np.int64)
    last = np.minimum(
        columns_total - 1, np.ceil(ends / CELL_PT - 0.5).astype(np.int64) - 1
    )
    spans = first <= last
    change = np.zeros((occupied.shape[0], columns_total + 1), dtype=np.int64)
    np.add.at(change, (rows[spans], first[spans]), 1)
    np.add.at(change, (rows[spans], last[spans] + 1), -1)
    occupied |= change.cumsum(axis=1)[:, :columns_total] > 0


def _mark_rectangle(
    occupied: np.ndarray,
    corners: tuple[float, float, float, float],
    *,
    width: float,
    height: float,
) -> None:
    """Mark the cells that a filled rectangle overlaps."""
    left, bottom, right, top = corners
    left, right = sorted((left, right))
    bottom, top = sorted((bottom, top))

    if right < 0.0 or left > width or top < 0.0 or bottom > height:
        return

    first_column, last_column = _interval_cells(
        low=left, high=right, length=width, cells=occupied.shape[1]
    )
    first_row, last_row = _interval_cells(
        low=bottom, high=top, length=height, cells=occupied.shape[0]
    )
    occupied[first_row : last_row + 1, first_column : last_column + 1] = True


def _subpath_edges(points: np.ndarray, *, close: bool) -> np.ndarray:
    ring = np.concatenate((points, points[:1])) if close else points

    return np.concatenate((ring[:-1], ring[1:]), axis=1)


def _subpaths(path: Path) -> Iterator[tuple[np.ndarray, bool]]:
    """Yield the subpaths of a path as point arrays and closed flags.

    Curves contribute their control points, so that each subpath is the
    control polygon of the drawn outline. Non-finite vertices split subpaths. A
    path without vertices, such as a line plotted from empty data, has none.
    """
    vertices = np.asarray(path.vertices, dtype=float)

    if len(vertices) == 0:
        return

    if path.codes is None:
        codes = np.full(len(vertices), Path.LINETO, dtype=Path.code_type)
        codes[:1] = Path.MOVETO
    else:
        codes = np.asarray(path.codes)

    starts = np.flatnonzero(codes == Path.MOVETO)

    for start, end in zip(starts, np.r_[starts[1:], len(codes)], strict=True):
        run_codes = codes[start:end]
        closed = bool(np.any(run_codes == Path.CLOSEPOLY))
        run = vertices[start:end][
            (run_codes != Path.CLOSEPOLY) & (run_codes != Path.STOP)
        ]
        finite = np.isfinite(run).all(axis=1)
        pieces = np.split(run, np.flatnonzero(~finite))

        for piece in pieces:
            kept = piece[np.isfinite(piece).all(axis=1)]

            if len(kept):
                yield kept, closed and len(pieces) == 1


def _axes_ink(axis: Axes) -> _Ink:
    """Collect the plotted ink of an axes.

    Returns:
        The ink in points, relative to the lower left corner of the axes.
    """
    axis_box = axis.get_window_extent()
    origin = np.array([axis_box.x0, axis_box.y0])
    points_per_pixel = POINTS_PER_INCH / axis.figure.dpi
    ink = _Ink()

    def to_points(display: np.ndarray) -> np.ndarray:
        return (np.asarray(display, dtype=float) - origin) * points_per_pixel

    def add_path(display_path: Path, *, stroke: bool, fill: bool) -> None:
        ink.add_outline(
            [(to_points(points), closed) for points, closed in _subpaths(display_path)],
            np.zeros((1, 2)),
            stroke=stroke,
            fill=fill,
        )

    def add_box(box: Bbox) -> None:
        ink.add_rectangle(to_points(np.array([[box.x0, box.y0], [box.x1, box.y1]])))

    for artist in axis.get_children():
        if not _is_plotted(axis=axis, artist=artist):
            continue

        if isinstance(artist, Line2D):
            path = artist.get_transform().transform_path(artist.get_path())
            add_path(
                path,
                stroke=artist.get_linestyle() not in NO_LINE_STYLES
                and artist.get_linewidth() > 0.0,
                fill=False,
            )
            _add_line_markers(ink, artist, centers=to_points(np.asarray(path.vertices)))
        elif isinstance(artist, QuadMesh | AxesImage):
            add_box(artist.get_window_extent())
        elif isinstance(artist, Collection):
            _add_collection(ink, artist, to_points=to_points, scale=points_per_pixel)
        elif isinstance(artist, Patch):
            add_path(
                artist.get_transform().transform_path(artist.get_path()),
                stroke=_visible_color(artist.get_edgecolor())
                and artist.get_linewidth() > 0.0,
                fill=artist.get_fill() and _visible_color(artist.get_facecolor()),
            )
        elif isinstance(artist, Text):
            if artist.get_text():
                add_box(artist.get_window_extent())

            bbox_patch = artist.get_bbox_patch()

            if bbox_patch is not None:
                add_box(bbox_patch.get_window_extent())
        else:
            add_box(artist.get_window_extent())

    return ink


def _is_plotted(*, axis: Axes, artist: Artist) -> bool:
    """Return whether an axes child is plotted content rather than decoration."""
    if not artist.get_visible() or artist is axis.patch:
        return False

    if isinstance(artist, Legend | Spine | Axis):
        return False

    return not isinstance(artist, Text) or artist in axis.texts


def _visible_color(color: ColorType) -> bool:
    return to_rgba(color)[3] > 0.0


def _add_line_markers(ink: _Ink, line: Line2D, *, centers: np.ndarray) -> None:
    marker = MarkerStyle(line.get_marker(), line.get_fillstyle())

    if marker.get_marker() in NO_LINE_STYLES:
        return

    outline_path = (
        marker.get_transform() + Affine2D().scale(line.get_markersize())
    ).transform_path(marker.get_path())
    ink.add_outline(
        list(_subpaths(outline_path)),
        centers[np.isfinite(centers).all(axis=1)],
        stroke=line.get_markeredgewidth() > 0.0
        and _visible_color(line.get_markeredgecolor()),
        fill=marker.is_filled() and _visible_color(line.get_markerfacecolor()),
    )


def _add_collection(
    ink: _Ink,
    collection: Collection,
    *,
    to_points: Callable[[np.ndarray], np.ndarray],
    scale: float,
) -> None:
    """Add the paths of a collection where ``Collection.draw`` places them.

    Path ``i`` is drawn through the per-path transform ``i``, then the master
    transform, and then shifted by offset ``i``, all indices cycling.
    """
    paths = collection.get_paths()

    if not paths:
        return

    master = collection.get_transform()
    offset_transform = collection.get_offset_transform()
    offsets = offset_transform.get_affine().transform(
        offset_transform.transform_non_affine(collection.get_offsets())
    )
    transforms = collection.get_transforms()
    paths = [master.transform_path_non_affine(path) for path in paths]
    indices = np.arange(max(len(paths), len(offsets), len(transforms)))
    fill, stroke = _collection_flags(collection, indices)
    shapes = np.stack(
        (
            indices % len(paths),
            indices % len(transforms) if len(transforms) else np.zeros_like(indices),
            fill,
            stroke,
        ),
        axis=1,
    )
    offset_points = to_points(offsets[indices % len(offsets)])

    for shape in np.unique(shapes, axis=0):
        transform = master.get_affine()

        if len(transforms):
            transform = Affine2D(transforms[shape[1]]) + transform

        drawn = transform.transform_path(paths[shape[0]])
        ink.add_outline(
            [(points * scale, closed) for points, closed in _subpaths(drawn)],
            offset_points[np.all(shapes == shape, axis=1)],
            stroke=bool(shape[3]),
            fill=bool(shape[2]),
        )


def _collection_flags(
    collection: Collection, indices: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return whether each drawn path of a collection is filled and stroked.

    Returns:
        The fill flags and the stroke flags, one per index.
    """
    facecolors = np.asarray(collection.get_facecolor(), dtype=float).reshape(-1, 4)
    edgecolors = np.asarray(collection.get_edgecolor(), dtype=float).reshape(-1, 4)
    linewidths = np.asarray(collection.get_linewidth(), dtype=float).reshape(-1)
    fill = _cycled(facecolors[:, 3] > 0.0, indices)
    stroke = _cycled(edgecolors[:, 3] > 0.0, indices) & _cycled(
        linewidths > 0.0, indices
    )

    return fill, stroke


def _cycled(values: np.ndarray, indices: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return np.zeros(len(indices), dtype=bool)

    return values[indices % len(values)]


def _snap_to_grid(*, axis: Axes, legend: Legend) -> Legend:
    """Move a legend at axes coordinates to the nearest major grid intersection.

    Returns:
        The legend.

    Raises:
        ValueError: If no grid intersection keeps the legend inside the axes.
    """
    legend_box = legend.get_window_extent().transformed(axis.transAxes.inverted())
    snapped = _nearest_snapped_box(axis=axis, box=legend_box)

    if snapped is None:
        msg = "No grid-snapped legend placement fits inside the axes."
        raise ValueError(msg)

    inset_x, inset_y = _frame_boundary_inset_axes(axis=axis, legend=legend)
    legend.set_in_layout(False)
    legend.set_bbox_to_anchor((0.0, 0.0, 1.0, 1.0), transform=axis.transAxes)
    legend.set_loc((
        _inset_boundary_anchor(value=snapped.x0, inset=inset_x),
        _inset_boundary_anchor(value=snapped.y0, inset=inset_y),
    ))

    return legend


def _nearest_snapped_box(*, axis: Axes, box: Bbox) -> Bbox | None:
    """Return the box moved to the nearest major grid intersection.

    Returns:
        The box with its lower left corner on the nearest major grid
        intersection that keeps it inside the axes, or None if none does.
    """
    x_grid, y_grid = _grid_values(axis)
    best_box = None
    best_score = (float("inf"), float("inf"))

    for grid_x in x_grid:
        for grid_y in y_grid:
            candidate = Bbox.from_bounds(grid_x, grid_y, box.width, box.height)

            if not _box_inside_axes(candidate):
                continue

            score = ((grid_x - box.x0) ** 2 + (grid_y - box.y0) ** 2, grid_x + grid_y)

            if score < best_score:
                best_score = score
                best_box = candidate

    return best_box


def _grid_values(axis: Axes) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return the major tick positions along x and along y in axes coordinates."""
    transform = axis.transData + axis.transAxes.inverted()
    x_ticks = axis.get_xticks()
    y_ticks = axis.get_yticks()
    x_values = transform.transform(
        np.column_stack((x_ticks, np.full(len(x_ticks), axis.get_ylim()[0])))
    )[:, 0]
    y_values = transform.transform(
        np.column_stack((np.full(len(y_ticks), axis.get_xlim()[0]), y_ticks))
    )[:, 1]

    return _sorted_unique_unit_values(x_values), _sorted_unique_unit_values(y_values)


def _sorted_unique_unit_values(values: Iterable[float]) -> tuple[float, ...]:
    rounded = {
        round(min(1.0, max(0.0, value)), UNIT_ROUND_DIGITS)
        for value in values
        if -EPSILON <= value <= 1.0 + EPSILON
    }
    rounded.update((0.0, 1.0))

    return tuple(sorted(rounded))


def _box_inside_axes(box: Bbox) -> bool:
    return (
        box.x0 >= -EPSILON
        and box.y0 >= -EPSILON
        and box.x1 <= 1.0 + EPSILON
        and box.y1 <= 1.0 + EPSILON
    )


def _frame_boundary_inset_axes(*, axis: Axes, legend: Legend) -> tuple[float, float]:
    axis_box = axis.get_window_extent()
    inset = 0.5 * legend.get_frame().get_linewidth() * axis.figure.dpi / POINTS_PER_INCH

    return inset / axis_box.width, inset / axis_box.height


def _inset_boundary_anchor(*, value: float, inset: float) -> float:
    if value <= EPSILON:
        return inset

    if value >= 1.0 - EPSILON:
        return 1.0 - inset

    return value
