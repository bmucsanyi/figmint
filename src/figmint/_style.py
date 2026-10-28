"""Matplotlib rcParams builders."""

from pathlib import Path
from typing import Literal

from cycler import cycler
from matplotlib import font_manager as mpl_font_manager

from figmint._colors import COLOR_THEMES, COLORMAP

GOLDEN_RATIO = (5.0**0.5 - 1.0) / 2.0
PAD_INCHES = 0.015
SAVEFIG_DPI = 600

THEMES = tuple(COLOR_THEMES)
VENUES = ("iclr", "neurips", "icml")
BACKENDS = ("matplotlib", "pgf")
TEX_COMPILERS = ("pdflatex", "xelatex", "lualatex")
MATH_FONTS = ("stix",)
VENUE_COLUMN_WIDTHS = {
    "iclr": {"full": 5.5},
    "neurips": {"full": 5.5},
    "icml": {"half": 3.25, "full": 6.75},
}
VENUE_CAPTION_FONT_SIZES = {
    "iclr": 10.0,
    "neurips": 10.0,
    "icml": 9.0,
}
VENUE_FONTS = {
    "iclr": "Times New Roman",
    "neurips": "Times New Roman",
    "icml": "Times New Roman",
}
VENUE_PREAMBLES = {
    "iclr": r"\usepackage{times}",
    "icml": r"\usepackage{times}",
    "neurips": (
        r"\renewcommand{\rmdefault}{ptm}"
        "\n"
        r"\renewcommand{\sfdefault}{phv}"
    ),
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
    backend: Literal["matplotlib", "pgf"] = "matplotlib",
    tex_compiler: Literal["pdflatex", "xelatex", "lualatex"] = "pdflatex",
    pgf_preamble: str | None = None,
    text_font: str | None = None,
    math_font: Literal["stix"] | None = None,
    font_weight: str | int = "normal",
    font_size: float | None = None,
    figure_size: tuple[float, float] | None = None,
    line_width: float = 0.5,
    grid_alpha: float = 0.16,
    height_to_width_ratio: float = GOLDEN_RATIO,
) -> dict[str, object]:
    """Return rcParams for publication figures and themed variants."""
    _validate_style_inputs(
        theme=theme,
        venue=venue,
        width_fraction=width_fraction,
        rows=rows,
        cols=cols,
        font_size=font_size,
        figure_size=figure_size,
        line_width=line_width,
        grid_alpha=grid_alpha,
        height_to_width_ratio=height_to_width_ratio,
        backend=backend,
        tex_compiler=tex_compiler,
        pgf_preamble=pgf_preamble,
        text_font=text_font,
        math_font=math_font,
    )

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
            backend=backend,
            text_font=VENUE_FONTS[venue] if text_font is None else text_font,
            math_font=math_font,
            font_weight=font_weight,
        ),
        **_backend_config(
            venue=venue,
            backend=backend,
            tex_compiler=tex_compiler,
            pgf_preamble=pgf_preamble,
            text_font=text_font,
            math_font=math_font,
        ),
        **_font_size_config(
            font_size=VENUE_CAPTION_FONT_SIZES[venue]
            if font_size is None
            else font_size,
        ),
        **_export_config(),
        **_line_config(line_width=line_width),
        **_axes_config(),
        **_theme_config(theme=theme, grid_alpha=grid_alpha),
    }


def _validate_style_inputs(
    *,
    theme: str,
    venue: str,
    width_fraction: float,
    rows: int,
    cols: int,
    font_size: float | None,
    figure_size: tuple[float, float] | None,
    line_width: float,
    grid_alpha: float,
    height_to_width_ratio: float,
    backend: str,
    tex_compiler: str,
    pgf_preamble: str | None,
    text_font: str | None,
    math_font: str | None,
) -> None:
    _require_choice(name="theme", value=theme, choices=THEMES)
    _require_choice(name="venue", value=venue, choices=VENUES)
    _require_choice(name="backend", value=backend, choices=BACKENDS)
    _require_choice(name="tex_compiler", value=tex_compiler, choices=TEX_COMPILERS)

    if math_font is not None:
        _require_choice(name="math_font", value=math_font, choices=MATH_FONTS)

    _require_positive(name="width_fraction", value=width_fraction)
    _require_positive(name="rows", value=rows)
    _require_positive(name="cols", value=cols)
    _require_positive(name="line_width", value=line_width)
    _require_positive(name="height_to_width_ratio", value=height_to_width_ratio)

    if not 0.0 <= grid_alpha <= 1.0:
        msg = "grid_alpha must be between 0.0 and 1.0."
        raise ValueError(msg)

    if font_size is not None:
        _require_positive(name="font_size", value=font_size)

    if figure_size is not None:
        _require_positive(name="figure_size width", value=figure_size[0])
        _require_positive(name="figure_size height", value=figure_size[1])

    _require_backend_knobs(
        backend=backend,
        tex_compiler=tex_compiler,
        pgf_preamble=pgf_preamble,
        text_font=text_font,
        math_font=math_font,
    )


def _require_choice(*, name: str, value: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        msg = f"Unknown {name} {value!r}. Expected one of {choices!r}."
        raise ValueError(msg)


def _require_positive(*, name: str, value: float) -> None:
    if value <= 0:
        msg = f"{name} must be positive."
        raise ValueError(msg)


def _require_backend_knobs(
    *,
    backend: str,
    tex_compiler: str,
    pgf_preamble: str | None,
    text_font: str | None,
    math_font: str | None,
) -> None:
    if backend == "matplotlib":
        if tex_compiler != "pdflatex":
            msg = "tex_compiler requires backend='pgf'."
            raise ValueError(msg)

        if pgf_preamble is not None:
            msg = "pgf_preamble requires backend='pgf'."
            raise ValueError(msg)

        return

    if pgf_preamble is not None and text_font is not None:
        msg = "text_font requires pgf_preamble=None."
        raise ValueError(msg)

    if pgf_preamble is not None and math_font is not None:
        msg = "math_font requires pgf_preamble=None."
        raise ValueError(msg)

    if tex_compiler == "pdflatex" and text_font is not None:
        msg = (
            "PGF text_font requires tex_compiler='xelatex' or tex_compiler='lualatex'."
        )
        raise ValueError(msg)


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
    return {
        "figure.figsize": figure_size
        if figure_size is not None
        else _venue_figure_size(
            venue=venue,
            column=column,
            width_fraction=width_fraction,
            rows=rows,
            cols=cols,
            height_to_width_ratio=height_to_width_ratio,
        ),
        "figure.constrained_layout.use": True,
        "figure.autolayout": False,
        "savefig.pad_inches": PAD_INCHES,
    }


def _venue_figure_size(
    *,
    venue: str,
    column: str,
    width_fraction: float,
    rows: int,
    cols: int,
    height_to_width_ratio: float,
) -> tuple[float, float]:
    widths = VENUE_COLUMN_WIDTHS[venue]

    if column not in widths:
        allowed = " or ".join(f"column={name!r}" for name in widths)
        msg = f"{venue} styles require {allowed}."
        raise ValueError(msg)

    width_in = widths[column] * width_fraction

    return width_in, height_to_width_ratio * (width_in / cols) * rows


def _font(
    *,
    backend: str,
    text_font: str,
    math_font: str | None,
    font_weight: str | int,
) -> dict[str, object]:
    return {
        "text.usetex": False,
        "font.family": "serif" if backend == "pgf" else text_font,
        "font.weight": font_weight,
        "axes.labelweight": font_weight,
        "axes.titleweight": font_weight,
        **({} if math_font is None else {"mathtext.fontset": math_font}),
    }


def _backend_config(
    *,
    venue: str,
    backend: str,
    tex_compiler: str,
    pgf_preamble: str | None,
    text_font: str | None,
    math_font: str | None,
) -> dict[str, object]:
    if backend == "matplotlib":
        return {}

    return {
        "backend": "pgf",
        "pgf.texsystem": tex_compiler,
        "pgf.preamble": pgf_preamble
        if pgf_preamble is not None
        else _pgf_preamble(
            venue=venue,
            tex_compiler=tex_compiler,
            text_font=text_font,
            math_font=math_font,
        ),
        "pgf.rcfonts": False,
    }


def _pgf_preamble(
    *,
    venue: str,
    tex_compiler: str,
    text_font: str | None,
    math_font: str | None,
) -> str:
    """Return the text setup of the venue or of ``text_font``, then the math font.

    STIX Two Math is the only math font; pdfLaTeX loads it through ``stix2`` and
    the Unicode engines through ``unicode-math``.
    """
    if text_font is None:
        lines = [VENUE_PREAMBLES[venue]]
    else:
        lines = [r"\usepackage{fontspec}", rf"\setmainfont{{{text_font}}}"]

    if math_font is not None and tex_compiler == "pdflatex":
        lines.append(r"\usepackage[notext]{stix2}")
    elif math_font is not None:
        lines.extend((r"\usepackage{unicode-math}", r"\setmathfont{STIX Two Math}"))

    return "\n".join(lines)


def _font_size_config(*, font_size: float) -> dict[str, object]:
    return {
        "font.size": font_size,
        "axes.labelsize": font_size,
        "legend.fontsize": font_size,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
        "axes.titlesize": font_size,
    }


def _export_config() -> dict[str, object]:
    return {
        "savefig.dpi": SAVEFIG_DPI,
        "savefig.transparent": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }


def _line_config(*, line_width: float) -> dict[str, object]:
    tick_major_width = line_width
    tick_minor_width = 0.5 * line_width
    tick_major_size = max(3.0, 3.0 * tick_major_width)
    tick_minor_size = max(2.0, 3.0 * tick_minor_width)

    return {
        "axes.linewidth": line_width,
        "lines.linewidth": 2.0 * line_width,
        "lines.markersize": 3.0,
        "lines.markeredgewidth": line_width,
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
    }


def _axes_config() -> dict[str, object]:
    return {
        "axes.grid": True,
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
    }


def _theme_config(*, theme: str, grid_alpha: float) -> dict[str, object]:
    colors = COLOR_THEMES[theme]

    return {
        **dict.fromkeys(BACKGROUND_COLOR_PARAMS, colors["background"]),
        **dict.fromkeys(TEXT_COLOR_PARAMS, colors["text"]),
        **dict.fromkeys(EDGE_COLOR_PARAMS, colors["edge"]),
        "axes.prop_cycle": cycler(color=colors["cycle"]),
        "grid.color": _grid_color(theme=theme),
        "grid.alpha": grid_alpha,
    }


def _grid_color(*, theme: str) -> str:
    """Return the grid color, the edge color of a theme or of latte for normal.

    The edge of the normal theme is black, too dark for grid lines.
    """
    if theme == "normal":
        return COLOR_THEMES["latte"]["edge"]

    return COLOR_THEMES[theme]["edge"]
