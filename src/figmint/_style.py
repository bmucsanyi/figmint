"""Matplotlib rcParams builders."""

from pathlib import Path
from typing import Literal

from cycler import cycler
from matplotlib import font_manager as mpl_font_manager

from figmint._colors import COLOR_THEMES

GOLDEN_RATIO = (5.0**0.5 - 1.0) / 2.0
PAD_INCHES = 0.015
FIGURE_SIZE_DIMENSIONS = 2

THEMES = tuple(COLOR_THEMES)
VENUES = ("iclr", "neurips", "icml")
BACKENDS = ("matplotlib", "pgf")
TEX_COMPILERS = ("pdflatex", "xelatex", "lualatex")
MATH_FONTS = ("stix",)
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
    resolved_font_size = _resolve_figure_text_size(venue=venue, font_size=font_size)
    resolved_text_font = _resolve_text_font(venue=venue, text_font=text_font)

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
            text_font=resolved_text_font,
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
            font_size=resolved_font_size,
        ),
        **_export_config(),
        **_line_config(line_width=line_width),
        **_theme_config(theme=theme, grid_alpha=grid_alpha),
    }


def _validate_style_inputs(
    *,
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
    _require_positive(name="width_fraction", value=width_fraction)
    _require_positive_integer(name="rows", value=rows)
    _require_positive_integer(name="cols", value=cols)
    _require_positive(name="line_width", value=line_width)
    _require_unit_interval(name="grid_alpha", value=grid_alpha)
    _require_positive(name="height_to_width_ratio", value=height_to_width_ratio)
    _require_known_backend(backend=backend)
    _require_known_tex_compiler(tex_compiler=tex_compiler)
    _require_known_math_font(math_font=math_font)
    _require_backend_knobs(
        backend=backend,
        tex_compiler=tex_compiler,
        pgf_preamble=pgf_preamble,
        text_font=text_font,
        math_font=math_font,
    )

    if font_size is not None:
        _require_font_size(font_size=font_size)

    _require_figure_size(figure_size=figure_size)


def _require_positive(*, name: str, value: float) -> None:
    if value <= 0:
        msg = f"{name} must be positive."
        raise ValueError(msg)


def _require_positive_integer(*, name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"{name} must be a positive integer."
        raise TypeError(msg)

    if value <= 0:
        msg = f"{name} must be a positive integer."
        raise ValueError(msg)


def _require_font_size(*, font_size: float) -> None:
    if font_size <= 1.0:
        msg = "font_size must be greater than 1.0."
        raise ValueError(msg)


def _require_figure_size(*, figure_size: tuple[float, float] | None) -> None:
    if figure_size is None:
        return

    if len(figure_size) != FIGURE_SIZE_DIMENSIONS:
        msg = "figure_size must contain exactly two dimensions."
        raise ValueError(msg)

    _require_positive(name="figure_size width", value=figure_size[0])
    _require_positive(name="figure_size height", value=figure_size[1])


def _require_unit_interval(*, name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        msg = f"{name} must be between 0.0 and 1.0."
        raise ValueError(msg)


def _require_known_backend(*, backend: str) -> None:
    if backend not in BACKENDS:
        msg = f"Unknown backend {backend!r}. Expected one of {BACKENDS!r}."
        raise ValueError(msg)


def _require_known_tex_compiler(*, tex_compiler: str) -> None:
    if tex_compiler not in TEX_COMPILERS:
        msg = (
            f"Unknown tex_compiler {tex_compiler!r}. Expected one of {TEX_COMPILERS!r}."
        )
        raise ValueError(msg)


def _require_known_math_font(*, math_font: str | None) -> None:
    if math_font is None:
        return

    if math_font not in MATH_FONTS:
        msg = f"Unknown math_font {math_font!r}. Expected one of {MATH_FONTS!r}."
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


def _theme_config(
    *,
    theme: str,
    grid_alpha: float,
) -> dict[str, object]:
    if theme not in THEMES:
        msg = f"Unknown theme {theme!r}. Expected one of {THEMES!r}."
        raise ValueError(msg)

    colors = COLOR_THEMES[theme]
    background = colors["background"]
    edge = colors["edge"]
    grid = _grid_color(theme=theme)
    text = colors["text"]

    return {
        **dict.fromkeys(BACKGROUND_COLOR_PARAMS, background),
        **dict.fromkeys(TEXT_COLOR_PARAMS, text),
        **dict.fromkeys(EDGE_COLOR_PARAMS, edge),
        "axes.prop_cycle": cycler(color=colors["cycle"]),
        "axes.grid": True,
        "grid.color": grid,
        "grid.alpha": grid_alpha,
        "grid.linestyle": "solid",
        "legend.edgecolor": "none",
        "legend.framealpha": 1.0,
        "legend.frameon": True,
        "savefig.transparent": False,
        "image.cmap": colors["colormap"],
    }


def _grid_color(*, theme: str) -> str:
    if theme == "normal":
        return COLOR_THEMES["latte"]["edge"]

    return COLOR_THEMES[theme]["edge"]


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
        _require_known_venue(venue=venue)
        return _figure_size_config(figure_size=figure_size)

    base_width_in = _base_width(venue=venue, column=column)

    return _figure_size_from_base_in(
        base_width_in=base_width_in,
        width_fraction=width_fraction,
        height_to_width_ratio=height_to_width_ratio,
        rows=rows,
        cols=cols,
    )


def _require_known_venue(*, venue: str) -> None:
    if venue not in VENUES:
        msg = _unknown_venue_message(venue=venue)
        raise ValueError(msg)


def _unknown_venue_message(*, venue: str) -> str:
    return f"Unknown venue {venue!r}. Expected one of {VENUES!r}."


def _base_width(*, venue: str, column: str) -> float:
    if venue == "icml":
        return _icml_width(column=column)

    if venue in {"iclr", "neurips"}:
        _require_full_width(column=column, venue=venue)
        return 5.5

    msg = _unknown_venue_message(venue=venue)
    raise ValueError(msg)


def _resolve_figure_text_size(*, venue: str, font_size: float | None) -> float:
    if font_size is not None:
        return font_size

    if venue in VENUE_CAPTION_FONT_SIZES:
        return VENUE_CAPTION_FONT_SIZES[venue]

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


def _export_config() -> dict[str, object]:
    return {
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
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
        "pgf.preamble": _pgf_preamble(
            venue=venue,
            tex_compiler=tex_compiler,
            pgf_preamble=pgf_preamble,
            text_font=text_font,
            math_font=math_font,
        ),
        "pgf.rcfonts": False,
    }


def _pgf_preamble(
    *,
    venue: str,
    tex_compiler: str,
    pgf_preamble: str | None,
    text_font: str | None,
    math_font: str | None,
) -> str:
    if pgf_preamble is not None:
        return pgf_preamble

    parts = [
        _pgf_text_preamble(
            venue=venue,
            text_font=text_font,
        ),
    ]

    if math_font is not None:
        parts.append(_pgf_math_preamble(math_font=math_font, tex_compiler=tex_compiler))

    return "\n".join(part for part in parts if part)


def _pgf_text_preamble(*, venue: str, text_font: str | None) -> str:
    if text_font is not None:
        return "\n".join(
            (
                r"\usepackage{fontspec}",
                rf"\setmainfont{{{text_font}}}",
            ),
        )

    if venue in VENUE_PREAMBLES:
        return VENUE_PREAMBLES[venue]

    msg = f"Unknown venue {venue!r}. Expected one of {VENUES!r}."
    raise ValueError(msg)


def _pgf_math_preamble(*, math_font: str, tex_compiler: str) -> str:
    if math_font == "stix" and tex_compiler == "pdflatex":
        return r"\usepackage[notext]{stix2}"

    if math_font == "stix":
        return (
            r"\usepackage{unicode-math}"
            "\n"
            r"\setmathfont{STIX Two Math}"
        )

    msg = f"Unknown math_font {math_font!r}. Expected one of {MATH_FONTS!r}."
    raise ValueError(msg)


def _resolve_text_font(*, venue: str, text_font: str | None) -> str:
    if text_font is not None:
        return text_font

    if venue in VENUE_FONTS:
        return VENUE_FONTS[venue]

    msg = f"Unknown venue {venue!r}. Expected one of {VENUES!r}."
    raise ValueError(msg)


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
        **_mathtext_config(math_font=math_font),
    }


def _mathtext_config(*, math_font: str | None) -> dict[str, object]:
    if math_font == "stix":
        return {"mathtext.fontset": "stix"}

    return {}


def _font_size_config(
    *,
    font_size: float,
) -> dict[str, object]:
    return {
        "font.size": font_size,
        "axes.labelsize": font_size,
        "legend.fontsize": font_size,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
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
        "legend.shadow": False,
        "legend.frameon": True,
        "legend.fancybox": False,
        "axes.axisbelow": True,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
