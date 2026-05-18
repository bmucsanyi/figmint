"""Render the README gallery images."""

import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from figmint import register_fonts, style

THEMES = ("normal", "latte", "frappe", "macchiato", "mocha")
CURVE_LABELS = ("baseline", "variant A", "variant B", "variant C")
CURVE_RATES = (0.045, 0.075, 0.12, 0.19)
SAMPLE_COUNT = 161
DPI = 300
TALK_FIGURE_SIZE = (7.5, 4.25)
SLIDE_FONT = "Roboto Condensed"
SLIDE_FONT_FILES = (
    Path.home() / "Library/Fonts/RobotoCondensed-VariableFont_wght.ttf",
    Path.home() / "Library/Fonts/RobotoCondensed-Italic-VariableFont_wght.ttf",
)


def _curve_points(*, rate: float) -> tuple[list[float], list[float]]:
    xs = [80.0 * index / (SAMPLE_COUNT - 1) for index in range(SAMPLE_COUNT)]
    ys = [0.018 + 0.982 * math.exp(-rate * x) for x in xs]

    return xs, ys


def _finish_axis(axis: Axes) -> None:
    axis.tick_params(direction="out")

    for spine in ("top", "right"):
        axis.spines[spine].set_visible(False)


def _draw_curves(axis: Axes) -> None:
    for index, rate in enumerate(CURVE_RATES):
        xs, ys = _curve_points(rate=rate)
        axis.plot(xs, ys, label=CURVE_LABELS[index])

    axis.set_xlim(0.0, 80.0)
    axis.set_ylim(1.0e-2, 1.2)
    axis.set_yscale("log")
    axis.set_xlabel(r"Step $t$")
    axis.set_ylabel(r"Relative value")
    axis.legend(ncols=2)
    _finish_axis(axis)


def _save_theme_preview(*, output_dir: Path, theme: str) -> None:
    with plt.rc_context(style(theme, venue="neurips", column="full")):
        figure, axis = plt.subplots()
        _draw_curves(axis)
        figure.savefig(output_dir / f"theme_{theme}.png", dpi=DPI)
        plt.close(figure)


def _save_talk_preview(*, output_dir: Path) -> None:
    register_fonts(*SLIDE_FONT_FILES)

    with plt.rc_context(
        style(
            "frappe",
            venue="icml",
            font=SLIDE_FONT,
            font_weight="light",
            font_size=13.0,
            figure_size=TALK_FIGURE_SIZE,
        )
    ):
        figure, axis = plt.subplots()
        _draw_curves(axis)
        figure.savefig(output_dir / "talk_frappe_overrides.png", dpi=DPI)
        plt.close(figure)


def render_gallery(output_dir: Path) -> None:
    """Render the README gallery PNGs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for theme in THEMES:
        _save_theme_preview(output_dir=output_dir, theme=theme)

    _save_talk_preview(output_dir=output_dir)


def main() -> None:
    """Render the gallery from the command line."""
    render_gallery(Path("gallery"))


if __name__ == "__main__":
    main()
