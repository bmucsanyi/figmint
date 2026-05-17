"""Catppuccin colors used by the matplotlib styles."""

from typing import TypedDict


class ColorTheme(TypedDict):
    background: str
    text: str
    edge: str
    cycle: tuple[str, ...]
    colormap: tuple[str, ...]


CATPPUCCIN_COLORMAPS = {
    "latte": (
        "#40a02b",
        "#179299",
        "#209fb5",
        "#1e66f5",
        "#8839ef",
        "#fe640b",
    ),
    "frappe": (
        "#a6d189",
        "#81c8be",
        "#85c1dc",
        "#8caaee",
        "#ca9ee6",
        "#ef9f76",
    ),
    "macchiato": (
        "#a6da95",
        "#8bd5ca",
        "#7dc4e4",
        "#8aadf4",
        "#c6a0f6",
        "#f5a97f",
    ),
    "mocha": (
        "#a6e3a1",
        "#94e2d5",
        "#74c7ec",
        "#89b4fa",
        "#cba6f7",
        "#fab387",
    ),
}


def _catppuccin_themes() -> dict[str, ColorTheme]:
    return {
        "latte": {
            "background": "#eff1f5",
            "text": "#4c4f69",
            "edge": "#9ca0b0",
            "cycle": (
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
            ),
            "colormap": CATPPUCCIN_COLORMAPS["latte"],
        },
        "frappe": {
            "background": "#303446",
            "text": "#c6d0f5",
            "edge": "#737994",
            "cycle": (
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
            ),
            "colormap": CATPPUCCIN_COLORMAPS["frappe"],
        },
        "macchiato": {
            "background": "#24273a",
            "text": "#cad3f5",
            "edge": "#6e738d",
            "cycle": (
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
            ),
            "colormap": CATPPUCCIN_COLORMAPS["macchiato"],
        },
        "mocha": {
            "background": "#1e1e2e",
            "text": "#cdd6f4",
            "edge": "#6c7086",
            "cycle": (
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
            ),
            "colormap": CATPPUCCIN_COLORMAPS["mocha"],
        },
    }


def _color_themes() -> dict[str, ColorTheme]:
    return {
        **CATPPUCCIN_THEMES,
        "normal": {
            **CATPPUCCIN_THEMES["latte"],
            "background": "#ffffff",
            "text": "#000000",
            "edge": "#000000",
        },
    }


CATPPUCCIN_THEMES = _catppuccin_themes()
COLOR_THEMES = _color_themes()
