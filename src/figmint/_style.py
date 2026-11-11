"""The look of a figure as matplotlib settings, see docs/style.md."""

from cycler import cycler

from figmint._colors import COLOR_THEMES, COLORMAP, Theme

LINE_WIDTH = 0.5
GRID_ALPHA = 0.16
SAVEFIG_DPI = 600
# The content of a figure stays this many points inside its canvas.
PAD_POINTS = 3.0
POINTS_PER_INCH = 72.0

BACKGROUND_COLOR_PARAMS = (
    "axes.facecolor",
    "figure.facecolor",
    "figure.edgecolor",
    "savefig.facecolor",
    "savefig.edgecolor",
    "legend.facecolor",
)
TEXT_COLOR_PARAMS = (
    "text.color",
    "axes.labelcolor",
    "axes.titlecolor",
    "xtick.labelcolor",
    "ytick.labelcolor",
    "legend.labelcolor",
)
EDGE_COLOR_PARAMS = (
    "axes.edgecolor",
    "xtick.color",
    "ytick.color",
    "patch.edgecolor",
)


def style(
    theme: Theme,
    *,
    figure_size: tuple[float, float],
    font_size: float,
    line_width: float = LINE_WIDTH,
    grid_alpha: float = GRID_ALPHA,
) -> dict[str, object]:
    """Return the settings of a figure that no document includes.

    matplotlib sets the text in its own fonts. A figure that a document
    includes is drawn through ``Document`` instead, which takes the size and
    the fonts from the document.

    Args:
        theme: The theme of the colors.
        figure_size: Width and height of the figure in inches.
        font_size: Size of every text in points.
        line_width: Width of the axes lines in points. Plot lines are twice as
            wide.
        grid_alpha: Opacity of the grid lines.

    Returns:
        rcParams to use in ``matplotlib.rc_context``.
    """
    _require_positive(name="figure_size width", value=figure_size[0])
    _require_positive(name="figure_size height", value=figure_size[1])
    _require_positive(name="font_size", value=font_size)

    return {
        "figure.figsize": figure_size,
        "text.usetex": False,
        **font_sizes(font_size),
        **look(theme, line_width=line_width, grid_alpha=grid_alpha),
    }


def font_sizes(font_size: float) -> dict[str, object]:
    """Return the settings that put every text of a figure at one size."""
    return {
        "font.size": font_size,
        "axes.labelsize": font_size,
        "axes.titlesize": font_size,
        "legend.fontsize": font_size,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
    }


def look(
    theme: str,
    *,
    line_width: float = LINE_WIDTH,
    grid_alpha: float = GRID_ALPHA,
) -> dict[str, object]:
    """Return the look of docs/style.md: layout, lines, axes, and the theme's colors.

    Returns:
        rcParams to use in ``matplotlib.rc_context``.

    Raises:
        ValueError: If the theme is unknown, the line width is not positive,
            or the grid opacity is outside [0, 1].
    """
    if theme not in COLOR_THEMES:
        msg = f"Unknown theme {theme!r}. Expected one of {tuple(COLOR_THEMES)!r}."
        raise ValueError(msg)

    _require_positive(name="line_width", value=line_width)

    if not 0.0 <= grid_alpha <= 1.0:
        msg = "grid_alpha must be between 0.0 and 1.0."
        raise ValueError(msg)

    colors = COLOR_THEMES[theme]

    return {
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.w_pad": PAD_POINTS / POINTS_PER_INCH,
        "figure.constrained_layout.h_pad": PAD_POINTS / POINTS_PER_INCH,
        "figure.autolayout": False,
        "savefig.dpi": SAVEFIG_DPI,
        "savefig.transparent": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.linewidth": line_width,
        "lines.linewidth": 2.0 * line_width,
        "lines.markersize": 3.0,
        "lines.markeredgewidth": line_width,
        "xtick.major.width": line_width,
        "ytick.major.width": line_width,
        "xtick.minor.width": 0.5 * line_width,
        "ytick.minor.width": 0.5 * line_width,
        "xtick.major.size": max(3.0, 3.0 * line_width),
        "ytick.major.size": max(3.0, 3.0 * line_width),
        "xtick.minor.size": max(2.0, 1.5 * line_width),
        "ytick.minor.size": max(2.0, 1.5 * line_width),
        "grid.linewidth": line_width,
        "patch.linewidth": line_width,
        "axes.xmargin": 0.05,
        "axes.ymargin": 0.05,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.linestyle": "solid",
        "legend.frameon": True,
        "legend.framealpha": 1.0,
        "legend.edgecolor": "none",
        "legend.fancybox": False,
        "legend.shadow": False,
        "image.cmap": COLORMAP,
        **dict.fromkeys(BACKGROUND_COLOR_PARAMS, colors["background"]),
        **dict.fromkeys(TEXT_COLOR_PARAMS, colors["text"]),
        **dict.fromkeys(EDGE_COLOR_PARAMS, colors["edge"]),
        "axes.prop_cycle": cycler(color=colors["cycle"]),
        "grid.color": colors["grid"],
        "grid.alpha": grid_alpha,
    }


def _require_positive(*, name: str, value: float) -> None:
    if value <= 0:
        msg = f"{name} must be positive."
        raise ValueError(msg)
