"""Matplotlib rcParams builders."""

from pathlib import Path

from cycler import cycler
from matplotlib import colormaps
from matplotlib import font_manager as mpl_font_manager
from matplotlib.colors import LinearSegmentedColormap

from figmint._colors import COLOR_THEMES

GOLDEN_RATIO = (5.0**0.5 - 1.0) / 2.0
PAD_INCHES = 0.015

THEMES = tuple(COLOR_THEMES)
VENUES = ("iclr", "neurips", "icml")
VENUE_FONT_SIZES = {
    "iclr": 9.0,
    "neurips": 9.0,
    "icml": 8.0,
}

VENUE_FONTS = {
    "iclr": "Times New Roman",
    "neurips": "Times New Roman",
    "icml": "Times New Roman",
}

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
    "grid.color",
    "legend.edgecolor",
    "patch.edgecolor",
)


def style(
    theme: str = "normal",
    *,
    venue: str,
    column: str = "full",
    width_fraction: float = 1.0,
    rows: int = 1,
    cols: int = 1,
    usetex: bool = False,
    font: str | None = None,
    font_weight: str | int = "normal",
    font_size: float | None = None,
    figure_size: tuple[float, float] | None = None,
    line_width: float = 0.5,
    grid_alpha: float = 0.22,
    height_to_width_ratio: float = GOLDEN_RATIO,
) -> dict[str, object]:
    """Return rcParams for publication figures and themed variants."""
    return {
        **_layout(
            venue=venue,
            column=column,
            width_fraction=width_fraction,
            rows=rows,
            cols=cols,
            figure_size=figure_size,
            height_to_width_ratio=height_to_width_ratio,
        ),
        **_font(
            venue=venue,
            usetex=usetex,
            font=_resolve_font(venue=venue, font=font),
            font_weight=font_weight,
        ),
        **_font_size_config(
            font_size=_resolve_font_size(venue=venue, font_size=font_size),
        ),
        **_line_config(line_width=line_width),
        **_theme_config(theme=theme, grid_alpha=grid_alpha),
    }


def register_fonts(*font_files: str | Path) -> None:
    """Register local font files with Matplotlib.

    Raises:
        FileNotFoundError: If a font file does not exist.
    """
    for font_file in font_files:
        path = Path(font_file).expanduser()

        if not path.exists():
            msg = f"Font file does not exist: {path}"
            raise FileNotFoundError(msg)

        mpl_font_manager.fontManager.addfont(path)


def _theme_config(
    *,
    theme: str,
    grid_alpha: float,
) -> dict[str, object]:
    if theme not in THEMES:
        msg = f"Unknown theme {theme!r}. Expected one of {THEMES!r}."
        raise ValueError(msg)

    colors = COLOR_THEMES[theme]
    _register_colormap(theme=theme, colors=colors["colormap"])
    background = colors["background"]
    edge = colors["edge"]
    text = colors["text"]

    return {
        **dict.fromkeys(BACKGROUND_COLOR_PARAMS, background),
        **dict.fromkeys(TEXT_COLOR_PARAMS, text),
        **dict.fromkeys(EDGE_COLOR_PARAMS, edge),
        "axes.prop_cycle": cycler(color=colors["cycle"]),
        "axes.grid": True,
        "grid.alpha": grid_alpha,
        "grid.linestyle": "solid",
        "legend.framealpha": 1.0,
        "savefig.transparent": False,
        "image.cmap": _colormap_name(theme=theme),
    }


def _register_colormap(*, theme: str, colors: tuple[str, ...]) -> None:
    name = _colormap_name(theme=theme)

    if name in colormaps:
        return

    colormaps.register(
        LinearSegmentedColormap.from_list(name, colors),
        name=name,
    )


def _colormap_name(*, theme: str) -> str:
    return f"figmint_{theme}"


def _layout(
    *,
    venue: str,
    column: str,
    width_fraction: float,
    rows: int,
    cols: int,
    figure_size: tuple[float, float] | None,
    height_to_width_ratio: float,
) -> dict[str, object]:
    if figure_size is not None:
        _base_width(venue=venue, column=column)
        return _figure_size_config(figure_size=figure_size)

    base_width_in = _base_width(venue=venue, column=column)

    return _figure_size_from_base_in(
        base_width_in=base_width_in,
        width_fraction=width_fraction,
        height_to_width_ratio=height_to_width_ratio,
        rows=rows,
        cols=cols,
    )


def _base_width(*, venue: str, column: str) -> float:
    if venue == "icml":
        return _icml_width(column=column)

    if venue in {"iclr", "neurips"}:
        _require_full_width(column=column, venue=venue)
        return 5.5

    msg = f"Unknown venue {venue!r}. Expected one of {VENUES!r}."
    raise ValueError(msg)


def _resolve_font_size(*, venue: str, font_size: float | None) -> float:
    if font_size is not None:
        return font_size

    if venue in VENUE_FONT_SIZES:
        return VENUE_FONT_SIZES[venue]

    msg = f"Unknown venue {venue!r}. Expected one of {VENUES!r}."
    raise ValueError(msg)


def _icml_width(*, column: str) -> float:
    if column == "half":
        return 3.25

    if column == "full":
        return 6.75

    msg = "ICML styles require column='half' or column='full'."
    raise ValueError(msg)


def _require_full_width(*, column: str, venue: str) -> None:
    if column != "full":
        msg = f"{venue} styles require column='full'."
        raise ValueError(msg)


def _figure_size_from_base_in(
    *,
    base_width_in: float,
    width_fraction: float,
    height_to_width_ratio: float,
    rows: int,
    cols: int,
) -> dict[str, object]:
    width_in = base_width_in * width_fraction
    subplot_width_in = width_in / cols
    subplot_height_in = height_to_width_ratio * subplot_width_in
    height_in = subplot_height_in * rows

    return _figure_size_config(figure_size=(width_in, height_in))


def _figure_size_config(*, figure_size: tuple[float, float]) -> dict[str, object]:
    return {
        "figure.figsize": figure_size,
        "figure.constrained_layout.use": True,
        "figure.autolayout": False,
        "savefig.pad_inches": PAD_INCHES,
    }


def _resolve_font(*, venue: str, font: str | None) -> str:
    if font is not None:
        return font

    if venue in VENUE_FONTS:
        return VENUE_FONTS[venue]

    msg = f"Unknown venue {venue!r}. Expected one of {VENUES!r}."
    raise ValueError(msg)


def _font(
    *,
    venue: str,
    usetex: bool,
    font: str,
    font_weight: str | int,
) -> dict[str, object]:
    if usetex:
        return _tex_font(
            venue=venue,
            font=font,
            font_weight=font_weight,
        )

    return _matplotlib_font(font=font, font_weight=font_weight)


def _matplotlib_font(*, font: str, font_weight: str | int) -> dict[str, object]:
    return {
        "text.usetex": False,
        "font.family": font,
        "font.weight": font_weight,
        "axes.labelweight": font_weight,
        "axes.titleweight": font_weight,
        "mathtext.fontset": "stix",
    }


def _tex_font(
    *,
    venue: str,
    font: str,
    font_weight: str | int,
) -> dict[str, object]:
    expected_font = _resolve_font(venue=venue, font=None)

    if font != expected_font:
        msg = f"usetex styles require font={expected_font!r} for venue={venue!r}."
        raise ValueError(msg)

    if font_weight != "normal":
        msg = "usetex styles require font_weight='normal'."
        raise ValueError(msg)

    preamble = _latex_preamble(venue=venue)

    return {
        "text.usetex": True,
        "font.family": font,
        "font.weight": font_weight,
        "axes.labelweight": font_weight,
        "axes.titleweight": font_weight,
        "text.latex.preamble": preamble,
    }


def _latex_preamble(*, venue: str) -> str:
    if venue == "neurips":
        return r"\renewcommand{\rmdefault}{ptm}\renewcommand{\sfdefault}{phv}"

    if venue in {"iclr", "icml"}:
        return r"\usepackage{times}"

    msg = f"Unknown venue {venue!r}. Expected one of {VENUES!r}."
    raise ValueError(msg)


def _font_size_config(*, font_size: float) -> dict[str, object]:
    small_size = font_size - 2.0

    return {
        "font.size": font_size,
        "axes.labelsize": font_size,
        "legend.fontsize": small_size,
        "xtick.labelsize": small_size,
        "ytick.labelsize": small_size,
        "axes.titlesize": font_size,
    }


def _line_config(*, line_width: float) -> dict[str, object]:
    tick_major_width = line_width
    tick_minor_width = 0.5 * line_width
    tick_major_size = max(3.0, 3.0 * tick_major_width)
    tick_minor_size = max(2.0, 3.0 * tick_minor_width)

    return {
        "axes.linewidth": line_width,
        "lines.linewidth": 2.0 * line_width,
        "xtick.major.width": tick_major_width,
        "ytick.major.width": tick_major_width,
        "xtick.minor.width": tick_minor_width,
        "ytick.minor.width": tick_minor_width,
        "xtick.major.size": tick_major_size,
        "ytick.major.size": tick_major_size,
        "xtick.minor.size": tick_minor_size,
        "ytick.minor.size": tick_minor_size,
        "grid.linewidth": line_width,
        "patch.linewidth": line_width,
        "legend.shadow": False,
        "legend.frameon": True,
        "legend.fancybox": False,
        "axes.axisbelow": True,
    }
