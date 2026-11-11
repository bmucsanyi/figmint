"""Plot functions for what settings cannot express, see docs/style.md."""

from collections.abc import Sequence

import numpy as np
from matplotlib import rcParams
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.collections import PathCollection, PolyCollection
from matplotlib.colorbar import Colorbar
from matplotlib.colors import to_rgb
from matplotlib.container import BarContainer
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch
from matplotlib.transforms import Bbox
from matplotlib.typing import ColorType
from numpy.typing import ArrayLike

from figmint._ticks import NumberFormatter

BAR_WIDTH = 0.4125
GROUPED_BAR_WIDTH = 0.22
BAR_GROUP_WIDTH = 0.8
BAR_TINT = 0.3
BOX_WIDTH = 0.55
WHISKER_WIDTH = 0.44
BOX_TINT = 0.12
BAND_ALPHA = 0.18
# Width of a colorbar and its distance from the axes, in points.
COLORBAR_WIDTH = 4.0
COLORBAR_GAP = 4.0
POINTS_PER_INCH = 72.0


def bar(
    axes: Axes,
    positions: ArrayLike,
    heights: ArrayLike,
    *,
    label: str | None = None,
    group: tuple[int, int] = (0, 1),
) -> BarContainer:
    """Draw vertical bars filled with 30% of their color over the background.

    The bars are outlined in their color.

    Args:
        axes: The axes.
        positions: Where the bars stand.
        heights: Their heights.
        label: Their legend entry.
        group: ``(index, count)`` for the index-th of ``count`` series that
            stand side by side at each position.

    Returns:
        The bars.
    """
    width, offset = _bar_layout(group)
    container = axes.bar(
        np.asarray(positions, dtype=float) + offset, heights, width=width, label=label
    )
    _tint_bars(axes, container)

    return container


def hbar(
    axes: Axes,
    positions: ArrayLike,
    widths: ArrayLike,
    *,
    label: str | None = None,
    group: tuple[int, int] = (0, 1),
) -> BarContainer:
    """Draw horizontal bars as ``bar`` does, with the grid along the value axis.

    Returns:
        The bars.
    """
    width, offset = _bar_layout(group)
    container = axes.barh(
        np.asarray(positions, dtype=float) + offset, widths, height=width, label=label
    )
    _tint_bars(axes, container)
    axes.grid(visible=False, axis="y")
    axes.grid(visible=True, axis="x")

    return container


def _bar_layout(group: tuple[int, int]) -> tuple[float, float]:
    """Return the width of a bar and its offset from the position for a group.

    Raises:
        ValueError: If the index is not below the count.
    """
    index, count = group

    if not 0 <= index < count:
        msg = f"group must be (index, count) with 0 <= index < count, got {group!r}."
        raise ValueError(msg)

    width = BAR_WIDTH if count == 1 else min(GROUPED_BAR_WIDTH, BAR_GROUP_WIDTH / count)

    return width, (index - (count - 1) / 2.0) * width


def _tint_bars(axes: Axes, container: BarContainer) -> None:
    background = axes.get_facecolor()

    for patch in container.patches:
        color = patch.get_facecolor()
        patch.set_facecolor(_tint(color, background, BAR_TINT))
        patch.set_edgecolor(color)


def _next_color(axes: Axes) -> ColorType:
    """Return the next color of the cycle of the axes, through a removed line."""
    (line,) = axes.plot([], [])
    line.remove()

    return line.get_color()


def _tint(
    color: ColorType, background: ColorType, amount: float
) -> tuple[float, float, float]:
    """Return ``amount`` of the color over the background.

    This is xcolor's ``color!amount!background``.
    """
    mixed = amount * np.asarray(to_rgb(color)) + (1.0 - amount) * np.asarray(
        to_rgb(background)
    )

    return (float(mixed[0]), float(mixed[1]), float(mixed[2]))


def area(axes: Axes, x: ArrayLike, y: ArrayLike, *, label: str | None = None) -> Line2D:
    """Draw a line with the area under it filled in its color at opacity 0.18.

    Returns:
        The line.
    """
    (line,) = axes.plot(x, y, label=label)
    axes.fill_between(
        x, 0.0, y, color=line.get_color(), alpha=BAND_ALPHA, linewidth=0.0
    )

    return line


def interval(
    axes: Axes, x: ArrayLike, lower: ArrayLike, upper: ArrayLike, *, color: ColorType
) -> PolyCollection:
    """Draw a band between two curves in a color at opacity 0.18, with no edge.

    Returns:
        The band.
    """
    return axes.fill_between(
        x, lower, upper, color=color, alpha=BAND_ALPHA, linewidth=0.0
    )


def scatter(
    axes: Axes, x: ArrayLike, y: ArrayLike, *, label: str | None = None
) -> PathCollection:
    """Draw filled discs with no edge, and no grid on the axes.

    Returns:
        The discs.
    """
    axes.grid(visible=False)

    return axes.scatter(x, y, linewidths=0.0, label=label)


def heatmap(
    axes: Axes,
    values: ArrayLike,
    *,
    extent: tuple[float, float, float, float] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
) -> AxesImage:
    """Draw a matrix as an image, ``values[0, 0]`` at the lower left, with no grid.

    Args:
        axes: The axes.
        values: The matrix, with y increasing along its rows.
        extent: ``(left, right, bottom, top)`` in data coordinates, or the cell
            indices when None.
        vmin: Value at the bottom of the colormap, or the smallest value when
            None.
        vmax: Value at the top of the colormap, or the largest value when None.

    Returns:
        The image.
    """
    axes.grid(visible=False)

    return axes.imshow(
        values,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=extent,
        vmin=vmin,
        vmax=vmax,
    )


def colorbar(axes: Axes, mappable: ScalarMappable) -> Colorbar:
    """Draw a colorbar 4 points wide, 4 points right of the axes and as tall.

    The colorbar has no frame, and its numbers are formatted by the look. Its
    axes follow the axes they belong to through a locator that reads the
    position the layout assigns, so constrained layout keeps room for its
    numbers.

    Returns:
        The colorbar.
    """
    figure = axes.figure

    def locate(*_: object) -> Bbox:
        box = axes.get_position(original=True)
        figure_width = figure.bbox.width / figure.dpi

        return Bbox.from_bounds(
            box.x1 + COLORBAR_GAP / POINTS_PER_INCH / figure_width,
            box.y0,
            COLORBAR_WIDTH / POINTS_PER_INCH / figure_width,
            box.height,
        )

    colorbar_axes = axes.inset_axes((1.0, 0.0, 0.1, 1.0))
    colorbar_axes.set_axes_locator(locate)
    bar_ = figure.colorbar(mappable, cax=colorbar_axes)
    colorbar_axes.spines["outline"].set_visible(False)
    colorbar_axes.yaxis.set_major_formatter(NumberFormatter())

    return bar_


def boxplot(
    axes: Axes,
    data: Sequence[ArrayLike],
    *,
    positions: Sequence[float] | None = None,
) -> dict[str, list[Line2D | PathPatch]]:
    """Draw boxes 0.55 wide with caps 0.44 wide, each in the next color of the cycle.

    A box is filled with 12% of its color over the background and outlined in
    it; its median is as wide as a plot line, its whiskers as an axis line.
    Fliers are not drawn.

    Args:
        axes: The axes.
        data: One sample per box.
        positions: Where the boxes stand, or 1, 2, ... when None.

    Returns:
        The artists, as ``Axes.boxplot`` returns them.
    """
    result = axes.boxplot(
        data,
        positions=positions,
        widths=BOX_WIDTH,
        capwidths=WHISKER_WIDTH,
        patch_artist=True,
        showfliers=False,
    )
    background = axes.get_facecolor()

    for index, box in enumerate(result["boxes"]):
        color = _next_color(axes)
        box.set_facecolor(_tint(color, background, BOX_TINT))
        box.set_edgecolor(color)
        box.set_linewidth(rcParams["axes.linewidth"])
        result["medians"][index].set_color(color)
        result["medians"][index].set_linewidth(rcParams["lines.linewidth"])

        for part in ("whiskers", "caps"):
            for line in result[part][2 * index : 2 * index + 2]:
                line.set_color(color)
                line.set_linewidth(rcParams["axes.linewidth"])

    return result
