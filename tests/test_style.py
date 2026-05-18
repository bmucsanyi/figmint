"""Tests for the public matplotlib style API."""

from collections.abc import Callable
from itertools import pairwise
from typing import Any

import matplotlib.pyplot as plt
import pytest
from matplotlib import colormaps, font_manager
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgb

import figmint
from figmint import register_fonts, style
from figmint._colors import (
    CATPPUCCIN_THEMES,
    COLOR_THEMES,
    REPAIRED_LATTE_CYCLE,
    THEME_COLORMAPS,
)


def value(config: dict[str, object], key: str) -> Any:
    return config[key]


def luminance(color: str) -> float:
    red, green, blue = to_rgb(color)

    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


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


def colormap_colors(theme: str) -> list[str]:
    colormap = COLOR_THEMES[theme]["colormap"]

    if isinstance(colormap, str):
        sampled = plt.get_cmap(colormap)

        return [to_hex(sampled(index / 255.0)) for index in range(256)]

    return list(colormap)


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


def test_public_api_exposes_style_and_font_registration() -> None:
    assert figmint.__all__ == ["register_fonts", "style"]
    assert not hasattr(figmint, "paper")
    assert not hasattr(figmint, "slides")


def test_color_tables_only_contain_style_roles() -> None:
    assert set(CATPPUCCIN_THEMES) == {"latte", "frappe", "macchiato", "mocha"}
    assert next(iter(COLOR_THEMES)) == "normal"
    assert set(COLOR_THEMES) == {
        "normal",
        "latte",
        "frappe",
        "macchiato",
        "mocha",
    }

    for theme in COLOR_THEMES.values():
        assert set(theme) == {"background", "text", "edge", "cycle", "colormap"}


def test_default_theme_is_publication_style() -> None:
    config = style(venue="icml", column="half")

    assert value(config, "figure.facecolor") == "#ffffff"
    assert value(config, "axes.facecolor") == "#ffffff"
    assert value(config, "savefig.facecolor") == "#ffffff"
    assert value(config, "text.color") == "#000000"
    assert value(config, "axes.labelcolor") == "#000000"
    assert value(config, "xtick.color") == "#000000"
    assert value(config, "ytick.color") == "#000000"
    assert value(config, "xtick.labelcolor") == "#000000"
    assert value(config, "ytick.labelcolor") == "#000000"
    assert value(config, "axes.edgecolor") == "#000000"
    assert value(config, "grid.color") == "#9ca0b0"
    assert value(config, "legend.edgecolor") == "#000000"
    assert value(config, "patch.edgecolor") == "#000000"
    assert value(config, "image.cmap") == "plasma"
    assert value(config, "axes.grid") is True
    assert value(config, "grid.alpha") == pytest.approx(0.16)
    assert value(config, "legend.frameon") is True
    assert value(config, "lines.markersize") == pytest.approx(3.0)
    assert value(config, "lines.markeredgewidth") == pytest.approx(0.5)
    assert value(config, "axes.prop_cycle").by_key()["color"] == list(
        REPAIRED_LATTE_CYCLE,
    )
    assert value(config, "font.size") == pytest.approx(8.0)


@pytest.mark.parametrize(
    ("theme", "background", "text", "edge"),
    [
        ("latte", "#eff1f5", "#4c4f69", "#9ca0b0"),
        ("frappe", "#303446", "#c6d0f5", "#737994"),
        ("macchiato", "#24273a", "#cad3f5", "#6e738d"),
        ("mocha", "#1e1e2e", "#cdd6f4", "#6c7086"),
    ],
)
def test_theme_backgrounds_and_text(
    theme: str,
    background: str,
    text: str,
    edge: str,
) -> None:
    config = style(theme, venue="icml")

    assert value(config, "figure.facecolor") == background
    assert value(config, "axes.facecolor") == background
    assert value(config, "savefig.facecolor") == background
    assert value(config, "figure.edgecolor") == background
    assert value(config, "savefig.edgecolor") == background
    assert value(config, "text.color") == text
    assert value(config, "axes.edgecolor") == edge
    assert value(config, "xtick.color") == edge
    assert value(config, "ytick.color") == edge
    assert value(config, "xtick.labelcolor") == text
    assert value(config, "ytick.labelcolor") == text
    assert value(config, "grid.color") == edge
    assert value(config, "axes.grid") is True
    assert value(config, "legend.edgecolor") == edge
    assert value(config, "legend.framealpha") == pytest.approx(1.0)
    assert value(config, "legend.frameon") is True
    assert value(config, "patch.edgecolor") == edge
    assert value(config, "image.cmap") == f"figmint_{theme}"
    assert value(config, "savefig.transparent") is False


@pytest.mark.parametrize("theme", ["latte", "frappe", "macchiato", "mocha"])
def test_color_cycles_are_exact(theme: str) -> None:
    assert (
        value(style(theme, venue="icml"), "axes.prop_cycle").by_key()["color"]
        == CATPPUCCIN_CYCLES[theme]
    )


def test_normal_color_cycle_is_repaired_latte_cycle() -> None:
    assert value(style("normal", venue="icml"), "axes.prop_cycle").by_key()[
        "color"
    ] == list(REPAIRED_LATTE_CYCLE)


def test_repaired_latte_cycle_has_white_background_contrast() -> None:
    assert min(contrast_against_white(color) for color in REPAIRED_LATTE_CYCLE) >= 3.0


def test_normal_grid_matches_latte_grid() -> None:
    normal = style("normal", venue="icml")
    latte = style("latte", venue="icml")

    assert value(normal, "axes.grid") == value(latte, "axes.grid")
    assert value(normal, "grid.color") == value(latte, "grid.color")
    assert value(normal, "grid.alpha") == value(latte, "grid.alpha")
    assert value(normal, "grid.linestyle") == value(latte, "grid.linestyle")


@pytest.mark.parametrize("theme", ["latte", "frappe", "macchiato", "mocha"])
def test_colormaps_are_exact(theme: str) -> None:
    config = style(theme, venue="icml")

    assert value(config, "image.cmap") == f"figmint_{theme}"

    with plt.rc_context(config):
        colormap = plt.get_cmap()

    assert colormap.name == f"figmint_{theme}"
    assert to_hex(colormap(0.0)) == THEME_COLORMAPS[theme][0]
    assert to_hex(colormap(1.0)) == THEME_COLORMAPS[theme][-1]


def test_normal_colormap_is_plasma() -> None:
    config = style("normal", venue="icml")

    assert value(config, "image.cmap") == "plasma"

    with plt.rc_context(config):
        colormap = plt.get_cmap()

    assert colormap.name == "plasma"
    assert COLOR_THEMES["normal"]["colormap"] == "plasma"


def test_owned_colormap_registration_overwrites_stale_entries() -> None:
    style("latte", venue="icml")
    stale_colormap = LinearSegmentedColormap.from_list(
        "figmint_latte",
        ("#ffffff", "#000000"),
    )

    with pytest.warns(UserWarning, match="Overwriting the cmap"):
        colormaps.register(stale_colormap, name="figmint_latte", force=True)

    with pytest.warns(UserWarning, match="Overwriting the cmap"):
        config = style("latte", venue="icml")

    with plt.rc_context(config):
        colormap = plt.get_cmap()

    assert colormap.name == "figmint_latte"
    assert to_hex(colormap(0.0)) == THEME_COLORMAPS["latte"][0]
    assert to_hex(colormap(1.0)) == THEME_COLORMAPS["latte"][-1]


@pytest.mark.parametrize("theme", ["latte", "frappe", "macchiato", "mocha"])
def test_colormaps_have_ordered_luminance(theme: str) -> None:
    color_luminances = [luminance(color) for color in colormap_colors(theme)]
    pairs = tuple(pairwise(color_luminances))
    increasing = all(left <= right for left, right in pairs)
    decreasing = all(left >= right for left, right in pairs)

    assert increasing or decreasing


@pytest.mark.parametrize("theme", ["normal", "latte", "frappe", "macchiato", "mocha"])
@pytest.mark.parametrize("venue", ["iclr", "neurips", "icml"])
def test_style_updates_matplotlib_rcparams(theme: str, venue: str) -> None:
    config = style(theme, venue=venue, column="full")

    plt.rcParams.update(config)

    with plt.rc_context(config):
        pass


@pytest.mark.parametrize(
    ("theme", "background"),
    [
        ("frappe", "#303446"),
        ("macchiato", "#24273a"),
        ("mocha", "#1e1e2e"),
    ],
)
def test_dark_figures_render_with_theme_background(
    theme: str,
    background: str,
) -> None:
    with plt.rc_context(style(theme, venue="icml")):
        figure, axis = plt.subplots()

        assert to_hex(figure.get_facecolor()) == background
        assert to_hex(axis.get_facecolor()) == background

        plt.close(figure)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: style("old", venue="icml"), "Unknown theme"),
        (lambda: style("Latte", venue="icml"), "Unknown theme"),
        (lambda: style("normal", venue="unknown"), "Unknown venue"),
        (lambda: style("normal", venue="ICML"), "Unknown venue"),
        (lambda: style("normal", venue="iclr", column="half"), "styles require"),
    ],
)
def test_unsupported_styles_fail_loudly(
    call: Callable[[], None],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        call()


def test_venue_layout_defaults_match_publication_layout() -> None:
    config = style(
        "normal",
        venue="icml",
        column="full",
        width_fraction=0.5,
        rows=2,
        cols=3,
        height_to_width_ratio=0.75,
    )

    figure_size = value(config, "figure.figsize")

    assert figure_size[0] == pytest.approx(3.375)
    assert figure_size[1] == pytest.approx(1.6875)


@pytest.mark.parametrize(
    ("venue", "column", "expected_width", "expected_font_size"),
    [
        ("icml", "half", 3.25, 8.0),
        ("icml", "full", 6.75, 8.0),
        ("iclr", "full", 5.5, 9.0),
        ("neurips", "full", 5.5, 9.0),
    ],
)
def test_conference_defaults_apply_without_size_overrides(
    venue: str,
    column: str,
    expected_width: float,
    expected_font_size: float,
) -> None:
    golden_ratio = (5.0**0.5 - 1.0) / 2.0
    config = style("normal", venue=venue, column=column)

    figure_size = value(config, "figure.figsize")

    assert value(config, "font.size") == expected_font_size
    assert value(config, "font.family") == "Times New Roman"
    assert figure_size[0] == expected_width
    assert figure_size[1] == pytest.approx(expected_width * golden_ratio)


def test_explicit_overrides_are_applied() -> None:
    config = style(
        "frappe",
        venue="icml",
        column="half",
        font="Roboto Condensed",
        font_weight="light",
        font_size=13.0,
        figure_size=(7.0, 3.5),
        line_width=0.8,
        grid_alpha=0.4,
    )

    assert value(config, "text.usetex") is False
    assert value(config, "font.family") == "Roboto Condensed"
    assert value(config, "font.weight") == "light"
    assert value(config, "axes.labelweight") == "light"
    assert value(config, "font.size") == pytest.approx(13.0)
    assert value(config, "figure.figsize") == (7.0, 3.5)
    assert value(config, "axes.linewidth") == pytest.approx(0.8)
    assert value(config, "lines.markeredgewidth") == pytest.approx(0.8)
    assert value(config, "grid.alpha") == pytest.approx(0.4)
    assert value(config, "figure.facecolor") == "#303446"


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: style("normal", venue="icml", width_fraction=0.0), "width_fraction"),
        (lambda: style("normal", venue="icml", rows=0), "rows"),
        (lambda: style("normal", venue="icml", cols=0), "cols"),
        (lambda: style("normal", venue="icml", line_width=0.0), "line_width"),
        (lambda: style("normal", venue="icml", grid_alpha=-0.1), "grid_alpha"),
        (lambda: style("normal", venue="icml", grid_alpha=1.1), "grid_alpha"),
    ],
)
def test_invalid_numeric_style_inputs_fail_loudly(
    call: Callable[[], None],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        call()


def test_explicit_figure_size_does_not_require_column_preset() -> None:
    config = style(
        "normal",
        venue="iclr",
        column="half",
        figure_size=(4.0, 2.0),
    )

    assert value(config, "figure.figsize") == (4.0, 2.0)
    assert value(config, "font.size") == pytest.approx(9.0)


def test_register_fonts_adds_font_files() -> None:
    font_file = font_manager.findfont("DejaVu Sans", fallback_to_default=False)
    register_fonts(font_file)
    config = style(
        "normal",
        venue="icml",
        font="DejaVu Sans",
        font_weight="light",
    )

    assert value(config, "font.family") == "DejaVu Sans"
    assert value(config, "font.weight") == "light"

    with plt.rc_context(config):
        resolved_font = font_manager.findfont(
            font_manager.FontProperties(family="DejaVu Sans", weight="light"),
            fallback_to_default=False,
        )

    assert resolved_font == font_file


def test_missing_font_file_fails_loudly() -> None:
    with pytest.raises(FileNotFoundError, match="Font file does not exist"):
        register_fonts("missing-font-file.ttf")


def test_usetex_uses_conference_font() -> None:
    config = style("normal", venue="icml", usetex=True)

    assert value(config, "text.usetex") is True
    assert value(config, "font.family") == "Times New Roman"
    assert value(config, "text.latex.preamble") == r"\usepackage{times}"


def test_usetex_rejects_custom_font() -> None:
    with pytest.raises(ValueError, match="usetex styles require font"):
        style(
            "normal",
            venue="icml",
            usetex=True,
            font="Roboto Condensed",
        )
