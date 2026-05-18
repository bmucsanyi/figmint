"""Post-plot layout helpers."""

from collections.abc import Iterable
from math import ceil
from typing import Any

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import Collection, PolyCollection
from matplotlib.image import AxesImage
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import Bbox

EPSILON = 1.0e-9
LOC_TUPLE_LENGTH = 2
UNIT_ROUND_DIGITS = 12
LEGEND_LOC_ATTRIBUTE = "_loc"
FIXED_LOC_CODES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
LOC_ANCHOR_FRACTIONS = {
    1: (1.0, 1.0),
    2: (0.0, 1.0),
    3: (0.0, 0.0),
    4: (1.0, 0.0),
    5: (1.0, 0.5),
    6: (0.0, 0.5),
    7: (1.0, 0.5),
    8: (0.5, 0.0),
    9: (0.5, 1.0),
    10: (0.5, 0.5),
}


def finish(axis: Axes) -> Axes:
    """Snap an existing legend to the axes grid and return the axes.

    Returns:
        The same axes, after any existing legend has been placed.
    """
    legend = axis.get_legend()

    if legend is None:
        return axis

    renderer = _draw(axis)
    loc = _legend_loc(legend)

    if loc == Legend.codes["best"]:
        _optimize_best_legend(axis=axis, legend=legend)
    else:
        _snap_existing_legend(axis=axis, legend=legend, loc=loc, renderer=renderer)

    _draw(axis)

    return axis


def _legend_loc(legend: Legend) -> int | tuple[float, float]:
    loc = getattr(legend, LEGEND_LOC_ATTRIBUTE)

    if isinstance(loc, str):
        return Legend.codes[loc]

    if isinstance(loc, int):
        return loc

    if isinstance(loc, tuple) and len(loc) == LOC_TUPLE_LENGTH:
        return loc

    msg = f"Unsupported legend location: {loc!r}."
    raise ValueError(msg)


def _draw(axis: Axes) -> RendererBase:
    axis.figure.canvas.draw()

    return _canvas_renderer(axis.figure.canvas)


def _canvas_renderer(canvas: Any) -> RendererBase:
    return canvas.get_renderer()


def _snap_existing_legend(
    *,
    axis: Axes,
    legend: Legend,
    loc: int | tuple[float, float],
    renderer: RendererBase,
) -> None:
    legend_box = _legend_box_axes(axis=axis, legend=legend, renderer=renderer)
    fraction = _anchor_fraction(loc)
    snapped = _nearest_snapped_box(axis=axis, box=legend_box, fraction=fraction)

    if snapped is None:
        msg = "No grid-snapped legend placement fits inside the axes."
        raise ValueError(msg)

    _apply_axes_box(axis=axis, legend=legend, box=snapped[0])


def _optimize_best_legend(
    *,
    axis: Axes,
    legend: Legend,
) -> None:
    handles, labels, title, frameon = _legend_parts(legend)
    entry_count = len(labels)
    best = None

    if entry_count == 0:
        return

    legend.remove()

    for ncols in range(1, entry_count + 1):
        for loc in FIXED_LOC_CODES:
            result = _best_candidate_score(
                axis=axis,
                handles=handles,
                labels=labels,
                title=title,
                frameon=frameon,
                entry_count=entry_count,
                ncols=ncols,
                loc=loc,
            )

            if result is None:
                continue

            if best is None or result[0] < best[0]:
                best = result

    if best is None:
        msg = "No grid-snapped legend placement fits inside the axes."
        raise ValueError(msg)

    _, best_box, best_ncols = best
    best_legend = axis.legend(
        handles,
        labels,
        loc="center",
        ncols=best_ncols,
        title=title,
        frameon=frameon,
    )
    _apply_axes_box(axis=axis, legend=best_legend, box=best_box)


def _best_candidate_score(
    *,
    axis: Axes,
    handles: list[Artist],
    labels: list[str],
    title: str,
    frameon: bool,
    entry_count: int,
    ncols: int,
    loc: int,
) -> tuple[tuple[float, ...], Bbox, int] | None:
    candidate = axis.legend(
        handles,
        labels,
        loc=loc,
        ncols=ncols,
        title=title,
        frameon=frameon,
    )
    renderer = _draw(axis)
    legend_box = _legend_box_axes(axis=axis, legend=candidate, renderer=renderer)
    snapped = _nearest_snapped_box(
        axis=axis,
        box=legend_box,
        fraction=_anchor_fraction(loc),
    )

    if snapped is None:
        candidate.remove()
        return None

    display_box = _axes_box_to_display(axis=axis, box=snapped[0])
    score = _candidate_score(
        axis=axis,
        box=display_box,
        ncols=ncols,
        entry_count=entry_count,
        loc=loc,
        snap_distance=snapped[1],
        renderer=renderer,
    )
    candidate.remove()

    return score, snapped[0], ncols


def _legend_parts(legend: Legend) -> tuple[list[Artist], list[str], str, bool]:
    return (
        _legend_handles(legend),
        [text.get_text() for text in legend.get_texts()],
        legend.get_title().get_text(),
        legend.get_frame_on(),
    )


def _legend_handles(legend: Legend) -> list[Artist]:
    handles = []

    for handle in legend.legend_handles:
        if handle is None:
            msg = "Cannot finish a legend entry without a handle."
            raise ValueError(msg)

        handles.append(handle)

    return handles


def _anchor_fraction(loc: int | tuple[float, float]) -> tuple[float, float]:
    if isinstance(loc, tuple):
        return (0.0, 0.0)

    if loc in LOC_ANCHOR_FRACTIONS:
        return LOC_ANCHOR_FRACTIONS[loc]

    msg = f"Unsupported legend location code: {loc!r}."
    raise ValueError(msg)


def _legend_box_axes(
    *,
    axis: Axes,
    legend: Legend,
    renderer: RendererBase,
) -> Bbox:
    return legend.get_window_extent(renderer).transformed(axis.transAxes.inverted())


def _nearest_snapped_box(
    *,
    axis: Axes,
    box: Bbox,
    fraction: tuple[float, float],
) -> tuple[Bbox, float] | None:
    x_grid, y_grid = _grid_values(axis)
    anchor_x = box.x0 + box.width * fraction[0]
    anchor_y = box.y0 + box.height * fraction[1]
    best_box = None
    best_score = (
        float("inf"),
        float("inf"),
        float("inf"),
    )

    for grid_x in x_grid:
        for grid_y in y_grid:
            candidate = Bbox.from_bounds(
                grid_x - box.width * fraction[0],
                grid_y - box.height * fraction[1],
                box.width,
                box.height,
            )

            if not _box_inside_axes(candidate):
                continue

            distance = (grid_x - anchor_x) ** 2 + (grid_y - anchor_y) ** 2
            movement = abs(candidate.x0 - box.x0) + abs(candidate.y0 - box.y0)
            score = (distance, movement, grid_x + grid_y)

            if score < best_score:
                best_score = score
                best_box = candidate

    if best_box is None:
        return None

    return best_box, best_score[0]


def _grid_values(axis: Axes) -> tuple[tuple[float, ...], tuple[float, ...]]:
    return _x_grid_values(axis), _y_grid_values(axis)


def _x_grid_values(axis: Axes) -> tuple[float, ...]:
    y_reference = axis.get_ylim()[0]
    transform = axis.transData + axis.transAxes.inverted()
    values = (transform.transform((tick, y_reference))[0] for tick in axis.get_xticks())

    return _sorted_unique_unit_values(values)


def _y_grid_values(axis: Axes) -> tuple[float, ...]:
    x_reference = axis.get_xlim()[0]
    transform = axis.transData + axis.transAxes.inverted()
    values = (transform.transform((x_reference, tick))[1] for tick in axis.get_yticks())

    return _sorted_unique_unit_values(values)


def _sorted_unique_unit_values(values: Iterable[float]) -> tuple[float, ...]:
    rounded = {
        round(min(1.0, max(0.0, value)), UNIT_ROUND_DIGITS)
        for value in values
        if -EPSILON <= value <= 1.0 + EPSILON
    }

    return tuple(sorted(rounded))


def _box_inside_axes(box: Bbox) -> bool:
    return (
        box.x0 >= -EPSILON
        and box.y0 >= -EPSILON
        and box.x1 <= 1.0 + EPSILON
        and box.y1 <= 1.0 + EPSILON
    )


def _apply_axes_box(*, axis: Axes, legend: Legend, box: Bbox) -> None:
    legend.set_bbox_to_anchor((0.0, 0.0, 1.0, 1.0), transform=axis.transAxes)
    legend.set_loc((box.x0, box.y0))


def _axes_box_to_display(*, axis: Axes, box: Bbox) -> Bbox:
    return box.transformed(axis.transAxes)


def _candidate_score(
    *,
    axis: Axes,
    box: Bbox,
    ncols: int,
    entry_count: int,
    loc: int,
    snap_distance: float,
    renderer: RendererBase,
) -> tuple[float, ...]:
    axis_box = axis.get_window_extent(renderer)
    width_ratio = box.width / axis_box.width
    height_ratio = box.height / axis_box.height
    rows = ceil(entry_count / ncols)
    balance = abs(ncols - rows)
    badness = _data_badness(axis=axis, legend_box=box, renderer=renderer)
    margin = _legend_margin_scale(
        axis=axis,
        legend_box=box,
        loc=loc,
        renderer=renderer,
        badness=badness,
    )

    return (
        badness,
        balance,
        -_score_float(margin),
        _score_float(width_ratio + height_ratio),
        FIXED_LOC_CODES.index(loc),
        _score_float(snap_distance),
        ncols,
    )


def _score_float(value: float) -> float:
    return round(value, UNIT_ROUND_DIGITS)


def _legend_margin_scale(
    *,
    axis: Axes,
    legend_box: Bbox,
    loc: int,
    renderer: RendererBase,
    badness: int,
) -> float:
    if badness > 0:
        return 1.0

    low = 1.0
    high = _axis_expansion_limit(
        axis=axis,
        box=legend_box,
        loc=loc,
        renderer=renderer,
    )

    if high <= low:
        return high

    while high - low > EPSILON:
        middle = 0.5 * (low + high)

        if middle in {low, high}:
            break

        expanded = _expanded_box(box=legend_box, loc=loc, scale=middle)

        if _data_badness(axis=axis, legend_box=expanded, renderer=renderer) == 0:
            low = middle
        else:
            high = middle

    return low


def _axis_expansion_limit(
    *,
    axis: Axes,
    box: Bbox,
    loc: int,
    renderer: RendererBase,
) -> float:
    axis_box = axis.get_window_extent(renderer)
    fraction = _anchor_fraction(loc)
    anchor_x = box.x0 + box.width * fraction[0]
    anchor_y = box.y0 + box.height * fraction[1]
    left_limit = _edge_scale(anchor=anchor_x, edge=box.x0, boundary=axis_box.x0)
    right_limit = _edge_scale(anchor=anchor_x, edge=box.x1, boundary=axis_box.x1)
    bottom_limit = _edge_scale(anchor=anchor_y, edge=box.y0, boundary=axis_box.y0)
    top_limit = _edge_scale(anchor=anchor_y, edge=box.y1, boundary=axis_box.y1)

    return min(
        left_limit,
        right_limit,
        bottom_limit,
        top_limit,
    )


def _edge_scale(*, anchor: float, edge: float, boundary: float) -> float:
    distance = abs(edge - anchor)

    if distance <= EPSILON:
        return float("inf")

    return abs(boundary - anchor) / distance


def _expanded_box(*, box: Bbox, loc: int, scale: float) -> Bbox:
    fraction = _anchor_fraction(loc)
    anchor_x = box.x0 + box.width * fraction[0]
    anchor_y = box.y0 + box.height * fraction[1]
    width = box.width * scale
    height = box.height * scale

    return Bbox.from_bounds(
        anchor_x - width * fraction[0],
        anchor_y - height * fraction[1],
        width,
        height,
    )


def _data_badness(*, axis: Axes, legend_box: Bbox, renderer: RendererBase) -> int:
    badness = 0

    for artist in axis.get_children():
        badness += _artist_badness(
            axis=axis,
            artist=artist,
            legend_box=legend_box,
            renderer=renderer,
        )

    return badness


def _artist_badness(
    *,
    axis: Axes,
    artist: Artist,
    legend_box: Bbox,
    renderer: RendererBase,
) -> int:
    badness = 0

    if not artist.get_visible() or isinstance(artist, Legend):
        return 0

    if isinstance(artist, Line2D):
        path = artist.get_transform().transform_path(artist.get_path())
        badness = _path_badness(legend_box=legend_box, path=path)

    elif isinstance(artist, Rectangle) and artist is not axis.patch:
        badness = legend_box.count_overlaps([artist.get_window_extent(renderer)])
    elif isinstance(artist, PolyCollection):
        badness = _poly_collection_badness(artist=artist, legend_box=legend_box)
    elif isinstance(artist, Collection):
        badness = _collection_badness(artist=artist, legend_box=legend_box)
    elif isinstance(artist, Patch) and artist is not axis.patch:
        path = artist.get_transform().transform_path(artist.get_path())
        badness = _path_badness(legend_box=legend_box, path=path)
    elif isinstance(artist, AxesImage | Text):
        badness = legend_box.count_overlaps([artist.get_window_extent(renderer)])

    return badness


def _path_badness(*, legend_box: Bbox, path: Path) -> int:
    badness = legend_box.count_contains(path.vertices)

    if path.intersects_bbox(legend_box, filled=False):
        badness += 1

    return badness


def _poly_collection_badness(
    *,
    artist: PolyCollection,
    legend_box: Bbox,
) -> int:
    badness = 0

    for path in artist.get_paths():
        transformed_path = artist.get_transform().transform_path(path)
        badness += _path_badness(legend_box=legend_box, path=transformed_path)

    return badness


def _collection_badness(*, artist: Collection, legend_box: Bbox) -> int:
    offsets = artist.get_offsets()
    transformed = artist.get_offset_transform().transform(offsets)

    return legend_box.count_contains(transformed)
