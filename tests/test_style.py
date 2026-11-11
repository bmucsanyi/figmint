"""Tests for the public matplotlib style API."""

import re
from collections.abc import Callable
from itertools import combinations
from math import atan2, cos, degrees, exp, radians, sin, sqrt
from pathlib import Path
from typing import Any

import matplotlib as mpl
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_hex, to_rgb
from matplotlib.figure import Figure

from figmint import style
from figmint._colors import COLOR_THEMES, NORMAL_CYCLE, Theme
from figmint._style import look

STY = Path(__file__).resolve().parents[1] / "tex" / "latex" / "figmint" / "figmint.sty"
FIGURE_SIZE = (3.25, 2.0)
PREFIXES = {
    "normal": "FigmintNormal",
    "latte": "FigmintLatte",
    "frappe": "FigmintFrappe",
    "macchiato": "FigmintMacchiato",
    "mocha": "FigmintMocha",
}
CYCLE_NAMES = (
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
)


def value(config: dict[str, object], key: str) -> Any:
    return config[key]


def normal_style() -> dict[str, object]:
    return style("normal", figure_size=FIGURE_SIZE, font_size=9.0)


def linearized_rgb_channel(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92

    return ((value + 0.055) / 1.055) ** 2.4


def contrast_against_white(color: str) -> float:
    red, green, blue = to_rgb(color)
    linear_red = linearized_rgb_channel(red)
    linear_green = linearized_rgb_channel(green)
    linear_blue = linearized_rgb_channel(blue)
    relative_luminance = (
        0.2126 * linear_red + 0.7152 * linear_green + 0.0722 * linear_blue
    )

    return 1.05 / (relative_luminance + 0.05)


def srgb_from_linearized_rgb_channel(value: float) -> float:
    clipped = min(1.0, max(0.0, value))

    if clipped <= 0.0031308:
        return 12.92 * clipped

    return 1.055 * clipped ** (1.0 / 2.4) - 0.055


def lab_from_rgb(red: float, green: float, blue: float) -> tuple[float, float, float]:
    linear_red = linearized_rgb_channel(red)
    linear_green = linearized_rgb_channel(green)
    linear_blue = linearized_rgb_channel(blue)
    x = 0.4124564 * linear_red + 0.3575761 * linear_green + 0.1804375 * linear_blue
    y = 0.2126729 * linear_red + 0.7151522 * linear_green + 0.0721750 * linear_blue
    z = 0.0193339 * linear_red + 0.1191920 * linear_green + 0.9503041 * linear_blue
    x_factor = lab_factor(x / 0.95047)
    y_factor = lab_factor(y)
    z_factor = lab_factor(z / 1.08883)

    return (
        116.0 * y_factor - 16.0,
        500.0 * (x_factor - y_factor),
        200.0 * (y_factor - z_factor),
    )


def lab_factor(value: float) -> float:
    if value > 216.0 / 24389.0:
        return value ** (1.0 / 3.0)

    return (24389.0 / 27.0 * value + 16.0) / 116.0


def lab_color(color: str) -> tuple[float, float, float]:
    return lab_from_rgb(*to_rgb(color))


def delta_e_2000(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    left_lightness, left_a, left_b = left
    right_lightness, right_a, right_b = right
    left_chroma = sqrt(left_a * left_a + left_b * left_b)
    right_chroma = sqrt(right_a * right_a + right_b * right_b)
    mean_chroma = 0.5 * (left_chroma + right_chroma)
    chroma_power = mean_chroma**7
    correction = 0.5 * (1.0 - sqrt(chroma_power / (chroma_power + 25.0**7)))
    left_adjusted_a = (1.0 + correction) * left_a
    right_adjusted_a = (1.0 + correction) * right_a
    left_adjusted_chroma = sqrt(left_adjusted_a * left_adjusted_a + left_b * left_b)
    right_adjusted_chroma = sqrt(
        right_adjusted_a * right_adjusted_a + right_b * right_b,
    )
    left_hue = hue_angle(left_b, left_adjusted_a, left_adjusted_chroma)
    right_hue = hue_angle(right_b, right_adjusted_a, right_adjusted_chroma)
    lightness_delta = right_lightness - left_lightness
    chroma_delta = right_adjusted_chroma - left_adjusted_chroma
    hue_delta = adjusted_hue_delta(
        left_hue=left_hue,
        right_hue=right_hue,
        left_chroma=left_adjusted_chroma,
        right_chroma=right_adjusted_chroma,
    )
    hue_component = (
        2.0
        * sqrt(left_adjusted_chroma * right_adjusted_chroma)
        * sin(radians(0.5 * hue_delta))
    )
    mean_lightness = 0.5 * (left_lightness + right_lightness)
    mean_adjusted_chroma = 0.5 * (left_adjusted_chroma + right_adjusted_chroma)
    mean_hue = adjusted_mean_hue(
        left_hue=left_hue,
        right_hue=right_hue,
        left_chroma=left_adjusted_chroma,
        right_chroma=right_adjusted_chroma,
    )
    hue_weight = (
        1.0
        - 0.17 * cos(radians(mean_hue - 30.0))
        + 0.24 * cos(radians(2.0 * mean_hue))
        + 0.32 * cos(radians(3.0 * mean_hue + 6.0))
        - 0.20 * cos(radians(4.0 * mean_hue - 63.0))
    )
    hue_rotation_angle = 30.0 * exp(-(((mean_hue - 275.0) / 25.0) ** 2))
    adjusted_chroma_power = mean_adjusted_chroma**7
    chroma_rotation = 2.0 * sqrt(
        adjusted_chroma_power / (adjusted_chroma_power + 25.0**7),
    )
    lightness_weight = 1.0 + (0.015 * (mean_lightness - 50.0) ** 2) / sqrt(
        20.0 + (mean_lightness - 50.0) ** 2
    )
    chroma_weight = 1.0 + 0.045 * mean_adjusted_chroma
    hue_scale = 1.0 + 0.015 * mean_adjusted_chroma * hue_weight
    rotation_term = -sin(radians(2.0 * hue_rotation_angle)) * chroma_rotation
    lightness_term = lightness_delta / lightness_weight
    chroma_term = chroma_delta / chroma_weight
    hue_term = hue_component / hue_scale

    return sqrt(
        lightness_term * lightness_term
        + chroma_term * chroma_term
        + hue_term * hue_term
        + rotation_term * chroma_term * hue_term,
    )


def hue_angle(b_value: float, a_value: float, chroma: float) -> float:
    if chroma <= 0.0:
        return 0.0

    return degrees(atan2(b_value, a_value)) % 360.0


def adjusted_hue_delta(
    *,
    left_hue: float,
    right_hue: float,
    left_chroma: float,
    right_chroma: float,
) -> float:
    if left_chroma * right_chroma <= 0.0:
        return 0.0

    hue_delta = right_hue - left_hue

    if hue_delta > 180.0:
        return hue_delta - 360.0

    if hue_delta < -180.0:
        return hue_delta + 360.0

    return hue_delta


def adjusted_mean_hue(
    *,
    left_hue: float,
    right_hue: float,
    left_chroma: float,
    right_chroma: float,
) -> float:
    if left_chroma * right_chroma <= 0.0:
        return left_hue + right_hue

    if abs(left_hue - right_hue) <= 180.0:
        return 0.5 * (left_hue + right_hue)

    if left_hue + right_hue < 360.0:
        return 0.5 * (left_hue + right_hue + 360.0)

    return 0.5 * (left_hue + right_hue - 360.0)


def simulated_cvd_lab(
    color: str,
    matrix: tuple[tuple[float, float, float], ...],
) -> tuple[float, float, float]:
    red, green, blue = to_rgb(color)
    linear = (
        linearized_rgb_channel(red),
        linearized_rgb_channel(green),
        linearized_rgb_channel(blue),
    )
    transformed = [
        srgb_from_linearized_rgb_channel(
            sum(row[index] * linear[index] for index in range(3)),
        )
        for row in matrix
    ]

    return lab_from_rgb(transformed[0], transformed[1], transformed[2])


def cols4all_pair_distance(left: str, right: str) -> float:
    distances = [
        delta_e_2000(lab_color(left), lab_color(right)),
        *(
            delta_e_2000(
                simulated_cvd_lab(left, matrix),
                simulated_cvd_lab(right, matrix),
            )
            for matrix in CVD_MATRICES.values()
        ),
    ]

    return min(distances)


def colors_satisfy_normal_cycle_constraints(colors: list[str]) -> bool:
    if any(contrast_against_white(color) < WHITE_CONTRAST_MIN for color in colors):
        return False

    for left, right in combinations(colors, 2):
        if cols4all_pair_distance(left, right) < COLS4ALL_DISTANCE_MIN:
            return False

    return True


def max_feasible_latte_prefix_length() -> int:
    latte_cycle = CATPPUCCIN_CYCLES["latte"]

    for length in range(len(latte_cycle) + 1):
        if not colors_satisfy_normal_cycle_constraints(latte_cycle[:length]):
            return length - 1

    return len(latte_cycle)


def count_unchanged_latte_prefix(colors: tuple[str, ...]) -> int:
    count = 0

    for color, original in zip(colors, CATPPUCCIN_CYCLES["latte"], strict=True):
        if color != original:
            return count

        count += 1

    return count


CATPPUCCIN_CYCLES = {
    "latte": [
        "#1e66f5",
        "#fe640b",
        "#40a02b",
        "#8839ef",
        "#d20f39",
        "#df8e1d",
        "#179299",
        "#ea76cb",
        "#209fb5",
        "#7287fd",
    ],
    "frappe": [
        "#8caaee",
        "#ef9f76",
        "#a6d189",
        "#ca9ee6",
        "#e78284",
        "#e5c890",
        "#81c8be",
        "#f4b8e4",
        "#85c1dc",
        "#babbf1",
    ],
    "macchiato": [
        "#8aadf4",
        "#f5a97f",
        "#a6da95",
        "#c6a0f6",
        "#ed8796",
        "#eed49f",
        "#8bd5ca",
        "#f5bde6",
        "#7dc4e4",
        "#b7bdf8",
    ],
    "mocha": [
        "#89b4fa",
        "#fab387",
        "#a6e3a1",
        "#cba6f7",
        "#f38ba8",
        "#f9e2af",
        "#94e2d5",
        "#f5c2e7",
        "#74c7ec",
        "#b4befe",
    ],
}

WHITE_CONTRAST_MIN = 3.0
COLS4ALL_DISTANCE_MIN = 10.0
CVD_MATRICES = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritan": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def sty_colors() -> dict[str, str]:
    r"""Read every named color of figmint.sty as a hex value, following \colorlet.

    Returns:
        The colors by name.
    """
    source = STY.read_text(encoding="utf-8")
    colors = {
        name: "#" + hex_value.lower()
        for name, hex_value in re.findall(
            r"\\definecolor\{(\w+)\}\{HTML\}\{([0-9a-fA-F]{6})\}", source
        )
    }

    for name, other in re.findall(r"\\colorlet\{(\w+)\}\{(\w+)\}", source):
        colors[name] = colors[other]

    return colors


@pytest.mark.parametrize("theme", list(COLOR_THEMES))
def test_theme_colors_agree_with_figmint_sty(theme: Theme) -> None:
    colors = sty_colors()
    prefix = PREFIXES[theme]
    expected = COLOR_THEMES[theme]

    assert colors[prefix + "Background"] == expected["background"]
    assert colors[prefix + "Text"] == expected["text"]
    assert colors[prefix + "Edge"] == expected["edge"]
    assert colors[prefix + "Grid"] == expected["grid"]
    assert (
        tuple(colors[prefix + "Cycle" + name] for name in CYCLE_NAMES)
        == expected["cycle"]
    )


def test_color_tables_hold_the_five_themes_with_their_roles() -> None:
    assert list(COLOR_THEMES) == ["normal", "latte", "frappe", "macchiato", "mocha"]

    for theme in COLOR_THEMES.values():
        assert set(theme) == {"background", "text", "edge", "grid", "cycle"}
        assert len(theme["cycle"]) == 10


def test_normal_style_is_the_look_on_white() -> None:
    config = normal_style()

    assert value(config, "figure.figsize") == FIGURE_SIZE
    assert value(config, "text.usetex") is False
    assert value(config, "figure.facecolor") == "#ffffff"
    assert value(config, "axes.facecolor") == "#ffffff"
    assert value(config, "savefig.facecolor") == "#ffffff"
    assert value(config, "text.color") == "#000000"
    assert value(config, "axes.edgecolor") == "#000000"
    assert value(config, "grid.color") == "#9ca0b0"
    assert value(config, "grid.alpha") == pytest.approx(0.16)
    assert value(config, "axes.grid") is True
    assert value(config, "axes.grid.axis") == "y"
    assert value(config, "axes.xmargin") == pytest.approx(0.05)
    assert value(config, "axes.ymargin") == pytest.approx(0.05)
    assert value(config, "figure.constrained_layout.use") is True
    assert value(config, "figure.constrained_layout.w_pad") == pytest.approx(3.0 / 72.0)
    assert value(config, "figure.constrained_layout.h_pad") == pytest.approx(3.0 / 72.0)
    assert value(config, "legend.edgecolor") == "none"
    assert value(config, "image.cmap") == "plasma"
    assert value(config, "axes.spines.top") is False
    assert value(config, "axes.spines.right") is False
    assert value(config, "axes.linewidth") == pytest.approx(0.5)
    assert value(config, "lines.linewidth") == pytest.approx(1.0)
    assert value(config, "lines.markersize") == pytest.approx(3.0)
    assert value(config, "axes.prop_cycle").by_key()["color"] == list(NORMAL_CYCLE)

    for key in ("font.size", "axes.labelsize", "axes.titlesize", "legend.fontsize"):
        assert value(config, key) == pytest.approx(9.0)

    assert value(config, "xtick.labelsize") == pytest.approx(9.0)
    assert value(config, "ytick.labelsize") == pytest.approx(9.0)
    assert value(config, "pdf.fonttype") == 42
    assert value(config, "savefig.dpi") == 600


def test_saved_pdf_embeds_images_at_600_dpi(tmp_path: Path) -> None:
    path = tmp_path / "image.pdf"

    with mpl.rc_context(normal_style()):
        figure = Figure(figsize=(2.0, 2.0))
        figure.set_layout_engine("none")
        FigureCanvasAgg(figure)
        axis = figure.add_axes((0.25, 0.25, 0.5, 0.5))
        axis.imshow([[0.0, 1.0], [1.0, 0.0]], aspect="auto")
        figure.savefig(path)

    size = re.search(rb"/Subtype /Image /Width (\d+) /Height (\d+)", path.read_bytes())

    assert size is not None
    assert (int(size[1]), int(size[2])) == (600, 600)


@pytest.mark.parametrize("theme", ["latte", "frappe", "macchiato", "mocha"])
def test_themes_set_their_colors(theme: Theme) -> None:
    config = style(theme, figure_size=FIGURE_SIZE, font_size=9.0)
    colors = COLOR_THEMES[theme]

    for key in (
        "figure.facecolor",
        "axes.facecolor",
        "savefig.facecolor",
        "legend.facecolor",
    ):
        assert value(config, key) == colors["background"]

    for key in (
        "text.color",
        "axes.labelcolor",
        "xtick.labelcolor",
        "ytick.labelcolor",
    ):
        assert value(config, key) == colors["text"]

    for key in ("axes.edgecolor", "xtick.color", "ytick.color", "patch.edgecolor"):
        assert value(config, key) == colors["edge"]

    assert value(config, "grid.color") == colors["grid"]
    assert value(config, "axes.prop_cycle").by_key()["color"] == list(colors["cycle"])


def test_repaired_latte_cycle_satisfies_normal_constraints() -> None:
    assert colors_satisfy_normal_cycle_constraints(list(NORMAL_CYCLE))


def test_repaired_latte_cycle_keeps_longest_feasible_latte_prefix() -> None:
    assert max_feasible_latte_prefix_length() == 1
    assert count_unchanged_latte_prefix(NORMAL_CYCLE) == 1
    assert NORMAL_CYCLE[0] == CATPPUCCIN_CYCLES["latte"][0]
    assert NORMAL_CYCLE[1] != CATPPUCCIN_CYCLES["latte"][1]


@pytest.mark.parametrize("theme", ["latte", "frappe", "macchiato", "mocha"])
def test_catppuccin_cycles_are_the_official_values(theme: Theme) -> None:
    assert list(COLOR_THEMES[theme]["cycle"]) == CATPPUCCIN_CYCLES[theme]


@pytest.mark.parametrize(
    ("theme", "background"),
    [("frappe", "#303446"), ("macchiato", "#24273a"), ("mocha", "#1e1e2e")],
)
def test_dark_figures_render_with_theme_background(
    theme: Theme, background: str
) -> None:
    with mpl.rc_context(style(theme, figure_size=FIGURE_SIZE, font_size=9.0)):
        figure = Figure()
        FigureCanvasAgg(figure)
        axis = figure.subplots()

        assert to_hex(figure.get_facecolor()) == background
        assert to_hex(axis.get_facecolor()) == background


def test_explicit_line_width_and_grid_alpha_are_applied() -> None:
    config = style(
        "frappe", figure_size=(7.0, 3.5), font_size=13.0, line_width=0.8, grid_alpha=0.4
    )

    assert value(config, "font.size") == pytest.approx(13.0)
    assert value(config, "figure.figsize") == (7.0, 3.5)
    assert value(config, "axes.linewidth") == pytest.approx(0.8)
    assert value(config, "lines.linewidth") == pytest.approx(1.6)
    assert value(config, "lines.markeredgewidth") == pytest.approx(0.8)
    assert value(config, "xtick.major.size") == pytest.approx(3.0)
    assert value(config, "grid.alpha") == pytest.approx(0.4)
    assert value(config, "figure.facecolor") == "#303446"


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: look("old"), "Unknown theme"),
        (
            lambda: look("Latte"),
            "Unknown theme",
        ),
        (
            lambda: style("normal", figure_size=(0.0, 2.0), font_size=9.0),
            "figure_size width",
        ),
        (
            lambda: style("normal", figure_size=(4.0, -1.0), font_size=9.0),
            "figure_size height",
        ),
        (lambda: style("normal", figure_size=FIGURE_SIZE, font_size=0.0), "font_size"),
        (
            lambda: style(
                "normal", figure_size=FIGURE_SIZE, font_size=9.0, line_width=0.0
            ),
            "line_width",
        ),
        (
            lambda: style(
                "normal", figure_size=FIGURE_SIZE, font_size=9.0, grid_alpha=-0.1
            ),
            "grid_alpha",
        ),
        (
            lambda: style(
                "normal", figure_size=FIGURE_SIZE, font_size=9.0, grid_alpha=1.1
            ),
            "grid_alpha",
        ),
    ],
)
def test_invalid_inputs_fail_loudly(call: Callable[[], object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        call()
