"""Color tables used by the matplotlib styles."""

from typing import TypedDict


class ColorTheme(TypedDict):
    background: str
    text: str
    edge: str
    cycle: tuple[str, ...]
    colormap: str


REPAIRED_LATTE_CYCLE = (
    "#1e66f5",
    "#fd6309",
    "#3d7e44",
    "#6c32b3",
    "#dd0337",
    "#b38e59",
    "#008f9a",
    "#d76dba",
    "#7b9b93",
    "#6490fe",
)


THEME_COLORMAPS = {
    "normal": "plasma",
    "latte": "plasma",
    "frappe": "plasma",
    "macchiato": "plasma",
    "mocha": "plasma",
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
            "colormap": THEME_COLORMAPS["latte"],
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
            "colormap": THEME_COLORMAPS["frappe"],
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
            "colormap": THEME_COLORMAPS["macchiato"],
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
            "colormap": THEME_COLORMAPS["mocha"],
        },
    }


def _color_themes() -> dict[str, ColorTheme]:
    return {
        "normal": {
            **CATPPUCCIN_THEMES["latte"],
            "background": "#ffffff",
            "cycle": REPAIRED_LATTE_CYCLE,
            "colormap": THEME_COLORMAPS["normal"],
            "text": "#000000",
            "edge": "#000000",
        },
        **CATPPUCCIN_THEMES,
    }


CATPPUCCIN_THEMES = _catppuccin_themes()
COLOR_THEMES = _color_themes()
