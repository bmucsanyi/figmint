"""Render preview figures for themes, layouts, and plot types."""

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from numpy.typing import NDArray

from figmint import register_fonts, style

THEMES = ("normal", "latte", "frappe", "macchiato", "mocha")
PREVIEW_EXTENSION = "pdf"
CURVE_LABELS = (
    r"$\eta = 0.25/L$",
    r"$\eta = 0.50/L$",
    r"$\eta = 0.75/L$",
    r"$\eta = 0.95/L$",
)
BAR_CONDITION_NUMBERS = (10.0, 40.0, 160.0)
BAR_TARGET_GAPS = (1.0e-2, 1.0e-4)
BAR_TARGET_LABELS = (r"$10^{-2}$", r"$10^{-4}$")
VENUE_LAYOUTS = (
    ("icml-half", "icml", "half", 1, 1, 1.0),
    ("icml-full", "icml", "full", 1, 2, 1.0),
    ("iclr-full", "iclr", "full", 2, 1, 1.0),
    ("neurips-full", "neurips", "full", 2, 2, 1.0),
)
STEP_FRACTIONS = (0.25, 0.50, 0.75, 0.95)
TALK_FIGURE_SIZE = (7.5, 4.25)
SURFACE_HEIGHT_TO_WIDTH_RATIO = 0.94
STEP_PANEL_INDEX = 1
CONDITION_PANEL_INDEX = 2
MAX_ARGUMENT_COUNT = 2
OUTPUT_DIR_ARGUMENT_COUNT = 2
SLIDE_FONT_FILES = (
    Path.home() / "Library/Fonts/RobotoCondensed-VariableFont_wght.ttf",
    Path.home() / "Library/Fonts/RobotoCondensed-Italic-VariableFont_wght.ttf",
)


def _relative_gap(
    *,
    condition_number: float,
    step_fraction: float,
    iteration: float,
) -> float:
    step_size = step_fraction / condition_number
    low_mode = (1.0 - step_size) ** iteration
    high_mode = (1.0 - step_size * condition_number) ** iteration
    objective = 0.5 * (low_mode**2 + condition_number * high_mode**2)
    initial_objective = 0.5 * (1.0 + condition_number)

    return objective / initial_objective


def _worst_case_gap(
    *,
    condition_number: float,
    step_fraction: float,
    iteration: float,
) -> float:
    contraction = 1.0 - step_fraction / condition_number

    return contraction ** (2.0 * iteration)


def _iterations_to_gap(
    *,
    condition_number: float,
    step_fraction: float,
    target_gap: float,
) -> int:
    contraction = (1.0 - step_fraction / condition_number) ** 2.0

    return math.ceil(math.log(target_gap) / math.log(contraction))


def _convergence_curves(
    *, condition_number: float
) -> tuple[list[float], tuple[list[float], ...]]:
    iterations = [float(index) for index in range(81)]
    curves = []

    for fraction in STEP_FRACTIONS:
        values = [
            _relative_gap(
                condition_number=condition_number,
                step_fraction=fraction,
                iteration=iteration,
            )
            for iteration in iterations
        ]

        curves.append(values)

    return (
        iterations,
        tuple(curves),
    )


def _step_sensitivity_points(
    *,
    condition_number: float,
    iteration: float,
) -> tuple[list[float], list[float]]:
    fractions = [0.10 + 0.05 * index for index in range(18)]
    gaps = [
        _relative_gap(
            condition_number=condition_number,
            step_fraction=fraction,
            iteration=iteration,
        )
        for fraction in fractions
    ]

    return fractions, gaps


def _condition_sensitivity_points(
    *,
    step_fraction: float,
    iteration: float,
) -> tuple[list[float], list[float]]:
    condition_numbers = [5.0, 10.0, 20.0, 40.0, 80.0, 160.0]
    gaps = [
        _worst_case_gap(
            condition_number=condition_number,
            step_fraction=step_fraction,
            iteration=iteration,
        )
        for condition_number in condition_numbers
    ]

    return condition_numbers, gaps


def _iteration_count_bars(
    *,
    step_fraction: float,
) -> tuple[list[str], tuple[list[int], ...]]:
    labels = [f"{condition_number:.0f}" for condition_number in BAR_CONDITION_NUMBERS]
    count_groups = []

    for target_gap in BAR_TARGET_GAPS:
        counts = [
            _iterations_to_gap(
                condition_number=condition_number,
                step_fraction=step_fraction,
                target_gap=target_gap,
            )
            for condition_number in BAR_CONDITION_NUMBERS
        ]

        count_groups.append(counts)

    return labels, tuple(count_groups)


def _quadratic_path(
    *,
    condition_number: float,
    step_fraction: float,
    steps: int,
) -> tuple[list[float], list[float]]:
    step_size = step_fraction / condition_number
    first_coordinates = []
    second_coordinates = []

    for iteration in range(steps + 1):
        first_coordinates.append((1.0 - step_size) ** iteration)
        second_coordinates.append((1.0 - step_size * condition_number) ** iteration)

    return first_coordinates, second_coordinates


def _contour_grid(
    *, condition_number: float
) -> tuple[list[float], list[float], list[list[float]]]:
    coordinates = [-0.05 + 0.05 * index for index in range(23)]
    values = []

    for second_coordinate in coordinates:
        row = [
            0.5 * (first_coordinate**2 + condition_number * second_coordinate**2)
            for first_coordinate in coordinates
        ]

        values.append(row)

    return coordinates, coordinates, values


def _surface_grid(
    *, condition_number: float
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    coordinates = np.linspace(-1.0, 1.0, 21)
    x_values, y_values = np.meshgrid(coordinates, coordinates)
    z_values = 0.5 * (x_values**2 + condition_number * y_values**2)

    return x_values, y_values, z_values


def _finish_axis(axis: Axes) -> None:
    axis.tick_params(direction="out")

    for spine in ("top", "right"):
        axis.spines[spine].set_visible(False)


def _draw_convergence_curves(
    axis: Axes,
    *,
    condition_number: float,
    curve_count: int,
) -> None:
    iterations, curves = _convergence_curves(condition_number=condition_number)

    for index, values in enumerate(curves[:curve_count]):
        axis.plot(iterations, values, label=CURVE_LABELS[index])

    axis.set_xlim(0.0, 80.0)
    axis.set_ylim(1.0e-2, 1.2)
    axis.set_yscale("log")
    axis.set_xlabel(r"Iteration $t$")
    axis.set_ylabel(r"Relative gap $\Delta_t/\Delta_0$")
    _finish_axis(axis)


def _draw_step_sensitivity(
    axis: Axes,
    *,
    condition_number: float,
    iteration: float,
) -> None:
    fractions, gaps = _step_sensitivity_points(
        condition_number=condition_number,
        iteration=iteration,
    )
    axis.plot(fractions, gaps, marker="o", markersize=2.5)
    axis.set_xlim(0.10, 0.95)
    axis.set_yscale("log")
    axis.set_xlabel(r"Step fraction $\eta L$")
    axis.set_ylabel(r"Relative gap $\Delta_t/\Delta_0$")
    _finish_axis(axis)


def _draw_iteration_bars(axis: Axes, *, step_fraction: float) -> None:
    labels, count_groups = _iteration_count_bars(step_fraction=step_fraction)
    width = 0.34
    base_positions = [float(index) for index in range(len(labels))]

    for index, counts in enumerate(count_groups):
        offset = (index - 0.5) * width
        positions = [position + offset for position in base_positions]
        axis.bar(
            positions,
            counts,
            width=width,
            label=BAR_TARGET_LABELS[index],
        )

    axis.set_xticks(base_positions, labels)
    axis.set_xlabel(r"Condition number $\kappa$")
    axis.set_ylabel(r"Iterations")
    axis.set_ylim(0.0, 1.12 * max(max(counts) for counts in count_groups))
    _add_legend(axis, columns=1)
    _finish_axis(axis)


def _draw_condition_sensitivity(
    axis: Axes,
    *,
    step_fraction: float,
    iteration: float,
) -> None:
    condition_numbers, gaps = _condition_sensitivity_points(
        step_fraction=step_fraction,
        iteration=iteration,
    )
    axis.loglog(condition_numbers, gaps, marker="o", markersize=2.5)
    axis.set_xlabel(r"Condition number $\kappa$")
    axis.set_ylabel(r"Worst-case gap")
    _finish_axis(axis)


def _draw_optimization_path(
    axis: Axes,
    *,
    condition_number: float,
    step_fraction: float,
) -> None:
    x_coordinates, y_coordinates, values = _contour_grid(
        condition_number=condition_number
    )
    axis.contour(
        x_coordinates,
        y_coordinates,
        values,
        levels=(0.02, 0.05, 0.10, 0.20, 0.50, 1.00, 2.00),
        linewidths=0.5,
        alpha=0.65,
    )
    path_x, path_y = _quadratic_path(
        condition_number=condition_number,
        step_fraction=step_fraction,
        steps=10,
    )
    axis.plot(path_x, path_y, marker="o", markersize=2.5, label=r"$x_t$")
    axis.scatter([0.0], [0.0], marker="x", s=18.0, label=r"$x^\star$")
    axis.set_xlim(-0.05, 1.05)
    axis.set_ylim(-0.05, 1.05)
    axis.set_xlabel(r"$x_1$")
    axis.set_ylabel(r"$x_2$")
    _finish_axis(axis)


def _draw_quadratic_surface(axis: Axes, *, condition_number: float) -> None:
    x_values, y_values, z_values = _surface_grid(condition_number=condition_number)
    axis.plot_surface(
        x_values,
        y_values,
        z_values,
        cmap=plt.get_cmap(),
        linewidth=0.0,
        antialiased=True,
        alpha=0.92,
    )
    axis.view_init(elev=26.0, azim=-130.0)
    axis.set_xlabel(r"$x_1$")
    axis.set_ylabel(r"$x_2$")
    axis.set_zlabel(r"$f(x)$")
    axis.grid(False)
    axis.tick_params(direction="out")
    axis.tick_params(axis="x", pad=1.5)
    axis.tick_params(axis="y", pad=1.5)
    axis.tick_params(axis="z", pad=1.5)


def _add_legend(axis: Axes, *, columns: int, location: str = "best") -> None:
    axis.legend(loc=location, ncols=columns)


def _draw_layout_panel(axis: Axes, *, index: int) -> None:
    panel_index = index % 4

    if panel_index == 0:
        _draw_convergence_curves(
            axis,
            condition_number=40.0,
            curve_count=3,
        )
        _add_legend(axis, columns=1)
    elif panel_index == STEP_PANEL_INDEX:
        _draw_iteration_bars(axis, step_fraction=1.0)
    elif panel_index == CONDITION_PANEL_INDEX:
        _draw_condition_sensitivity(
            axis,
            step_fraction=0.75,
            iteration=40.0,
        )
    else:
        _draw_optimization_path(
            axis,
            condition_number=12.0,
            step_fraction=0.85,
        )
        _add_legend(axis, columns=1)


def _render_theme_previews(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for theme in THEMES:
        with plt.rc_context(style(theme, venue="neurips", column="full")):
            figure, axis = plt.subplots()
            _draw_convergence_curves(
                axis,
                condition_number=40.0,
                curve_count=4,
            )
            _add_legend(axis, columns=2)
            figure.savefig(output_dir / f"theme_{theme}.{PREVIEW_EXTENSION}")
            plt.close(figure)


def _render_layout_previews(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for label, venue, column, rows, cols, width_fraction in VENUE_LAYOUTS:
        with plt.rc_context(
            style(
                "normal",
                venue=venue,
                column=column,
                rows=rows,
                cols=cols,
                width_fraction=width_fraction,
            )
        ):
            figure, axes = plt.subplots(rows, cols, squeeze=False)

            for index, axis in enumerate(axes.flat):
                _draw_layout_panel(axis, index=index)

            filename = f"layout_{label}_{rows}x{cols}.{PREVIEW_EXTENSION}"
            figure.savefig(output_dir / filename)
            plt.close(figure)


def _render_plot_type_previews(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with plt.rc_context(style("normal", venue="icml", column="half")):
        figure, axis = plt.subplots()
        _draw_convergence_curves(axis, condition_number=40.0, curve_count=4)
        _add_legend(axis, columns=2)
        figure.savefig(output_dir / f"line_convergence.{PREVIEW_EXTENSION}")
        plt.close(figure)

    with plt.rc_context(style("normal", venue="icml", column="half")):
        figure, axis = plt.subplots()
        _draw_iteration_bars(axis, step_fraction=1.0)
        figure.savefig(output_dir / f"bar_iteration_counts.{PREVIEW_EXTENSION}")
        plt.close(figure)

    with plt.rc_context(style("normal", venue="icml", column="half")):
        figure, axis = plt.subplots()
        _draw_optimization_path(
            axis,
            condition_number=12.0,
            step_fraction=0.85,
        )
        _add_legend(axis, columns=1)
        figure.savefig(output_dir / f"contour_optimization_path.{PREVIEW_EXTENSION}")
        plt.close(figure)

    with plt.rc_context(
        style(
            "normal",
            venue="icml",
            column="half",
            height_to_width_ratio=SURFACE_HEIGHT_TO_WIDTH_RATIO,
        )
    ):
        figure = plt.figure()
        axis = figure.add_subplot(111, projection="3d")
        _draw_quadratic_surface(axis, condition_number=8.0)
        figure.savefig(output_dir / f"surface_quadratic.{PREVIEW_EXTENSION}")
        plt.close(figure)


def _render_talk_preview(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    register_fonts(*SLIDE_FONT_FILES)

    with plt.rc_context(
        style(
            "frappe",
            venue="icml",
            font="Roboto Condensed",
            font_weight="light",
            font_size=13.0,
            figure_size=TALK_FIGURE_SIZE,
        )
    ):
        figure, axis = plt.subplots()
        _draw_convergence_curves(
            axis,
            condition_number=40.0,
            curve_count=4,
        )
        _add_legend(axis, columns=2)
        figure.savefig(output_dir / f"talk_frappe_overrides.{PREVIEW_EXTENSION}")
        plt.close(figure)


def render_previews(output_dir: Path) -> None:
    """Render all preview PDFs under the requested output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _render_theme_previews(output_dir / "themes")
    _render_layout_previews(output_dir / "layouts")
    _render_plot_type_previews(output_dir / "plot_types")
    _render_talk_preview(output_dir / "themes")


def _output_directory() -> Path:
    if len(sys.argv) > MAX_ARGUMENT_COUNT:
        msg = "Usage: uv run preview.py [output_dir]"
        raise SystemExit(msg)

    if len(sys.argv) == OUTPUT_DIR_ARGUMENT_COUNT:
        return Path(sys.argv[1])

    return Path("theme_preview")


def main() -> None:
    """Render previews from the command line."""
    output_dir = _output_directory()
    render_previews(output_dir)
    print(f"Wrote previews to {output_dir}")


if __name__ == "__main__":
    main()
