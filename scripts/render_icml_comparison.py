"""Render shared data and Matplotlib figures for the ICML comparison."""

import math
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from figmint import export_table, finish, style

HALF_WIDTH_IN = 3.25
FULL_WIDTH_IN = 6.75
HALF_HEIGHT_IN = 2.05
FULL_GROUP_HEIGHT_IN = 4.25
LINE_SERIES = (
    ("baseline", "baseline", 0.23, 0.00),
    ("adapter", "adapter", 0.31, 0.04),
    ("ensemble", "ensemble", 0.38, 0.07),
)
BAR_SERIES = (
    ("baseline", "baseline", (0.61, 0.66, 0.69, 0.73, 0.76)),
    ("adapter", "adapter", (0.66, 0.70, 0.74, 0.78, 0.81)),
    ("ensemble", "ensemble", (0.69, 0.75, 0.79, 0.83, 0.86)),
)
BOX_SERIES = (
    ("small", "small"),
    ("medium", "medium"),
    ("large", "large"),
    ("xlarge", "x-large"),
)
SAMPLE_COUNT = 61
SCATTER_COUNT = 36


def render_comparison(output_dir: Path) -> None:
    """Write data tables and Matplotlib figure PDFs."""
    data_dir = output_dir / "data"
    mpl_dir = output_dir / "mpl"
    data_dir.mkdir(parents=True, exist_ok=True)
    mpl_dir.mkdir(parents=True, exist_ok=True)

    data = _write_data(data_dir=data_dir)
    _write_mpl_figures(mpl_dir=mpl_dir, data=data)


def _write_data(data_dir: Path) -> dict[str, Any]:
    xs = [float(index) for index in range(11)]
    lines = _line_data(xs=xs)
    heatmap = _heatmap_data()
    scatter = _scatter_data()
    interval = _interval_data()
    log_data = _log_data()
    hist = _histogram_data()
    boxes = _box_data()

    for key, values in lines.items():
        export_table(
            data_dir / f"line-{key}.tsv",
            x=xs,
            y=values[0],
            yerr=values[1],
        )

    heatmap_x, heatmap_y, heatmap_z = heatmap
    export_table(data_dir / "heatmap.tsv", x=heatmap_x, y=heatmap_y, z=heatmap_z)

    for key, _, values in BAR_SERIES:
        export_table(
            data_dir / f"bars-{key}.tsv",
            x=[1, 2, 3, 4, 5],
            y=values,
        )

    export_table(
        data_dir / "scatter.tsv",
        x=scatter[0],
        y=scatter[1],
        score=scatter[2],
    )
    export_table(
        data_dir / "interval.tsv",
        x=interval[0],
        y=interval[1],
        lower=interval[2],
        upper=interval[3],
    )

    for key, values in log_data.items():
        export_table(
            data_dir / f"log-{key}.tsv",
            x=values[0],
            y=values[1],
            yerr=values[2],
        )

    export_table(data_dir / "histogram.tsv", x=hist[0], y=hist[1])

    for key, values in boxes.items():
        export_table(data_dir / f"box-{key}.tsv", y=values)

    return {
        "xs": xs,
        "lines": lines,
        "heatmap": heatmap,
        "scatter": scatter,
        "interval": interval,
        "log": log_data,
        "histogram": hist,
        "boxes": boxes,
    }


def _line_data(*, xs: list[float]) -> dict[str, tuple[list[float], list[float]]]:
    data = {}

    for key, _, rate, offset in LINE_SERIES:
        ys = [
            0.42
            + offset
            + 0.44 * (1.0 - math.exp(-rate * x))
            + 0.018 * math.sin(0.9 * x)
            for x in xs
        ]
        yerr = [0.018 + 0.006 * (1.0 + math.sin(0.7 * x + offset)) for x in xs]
        data[key] = (ys, yerr)

    return data


def _heatmap_data() -> tuple[list[int], list[int], list[list[float]]]:
    xs = list(range(6))
    ys = list(range(5))
    values = [
        [0.18 + 0.09 * x + 0.11 * y + 0.12 * math.sin(0.7 * x + 0.45 * y) for x in xs]
        for y in ys
    ]

    return xs, ys, values


def _scatter_data() -> tuple[list[float], list[float], list[float]]:
    xs = []
    ys = []
    scores = []

    for index in range(SCATTER_COUNT):
        column = index % 9
        row = index // 9
        x_value = 0.35 + 0.52 * column + 0.04 * math.sin(index)
        y_value = 0.22 + 0.18 * row + 0.13 * math.sin(0.7 * column)
        score = 0.15 + 0.018 * index + 0.08 * math.cos(0.6 * index)
        xs.append(x_value)
        ys.append(y_value)
        scores.append(score)

    return xs, ys, scores


def _interval_data() -> tuple[list[float], list[float], list[float], list[float]]:
    xs = [6.0 * index / (SAMPLE_COUNT - 1) for index in range(SAMPLE_COUNT)]
    ys = [0.74 * math.exp(-0.32 * x) + 0.15 + 0.025 * math.sin(2.1 * x) for x in xs]
    radius = [0.045 + 0.02 * math.exp(-0.25 * x) for x in xs]
    lower = [y - width for y, width in zip(ys, radius, strict=True)]
    upper = [y + width for y, width in zip(ys, radius, strict=True)]

    return xs, ys, lower, upper


def _log_data() -> dict[str, tuple[list[int], list[float], list[float]]]:
    xs = list(range(9))
    train = [0.96 * math.exp(-0.58 * x) + 0.011 for x in xs]
    valid = [0.84 * math.exp(-0.46 * x) + 0.023 + 0.006 * math.sin(0.9 * x) for x in xs]
    train_err = [0.018 * value for value in train]
    valid_err = [0.035 * value for value in valid]

    return {
        "train": (xs, train, train_err),
        "valid": (xs, valid, valid_err),
    }


def _histogram_data() -> tuple[list[float], list[float]]:
    centers = [-2.4 + 0.4 * index for index in range(13)]
    counts = [
        0.8 * math.exp(-0.5 * (center + 0.65) ** 2)
        + 0.55 * math.exp(-0.5 * ((center - 0.85) / 0.65) ** 2)
        for center in centers
    ]

    return centers, counts


def _box_data() -> dict[str, list[float]]:
    data = {}

    for index, (key, _) in enumerate(BOX_SERIES):
        center = 0.42 + 0.08 * index
        spread = 0.08 + 0.015 * index
        values = [
            center
            + spread * math.sin(0.75 * sample)
            + 0.035 * math.cos(0.31 * sample + index)
            for sample in range(28)
        ]
        data[key] = values

    return data


def _write_mpl_figures(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    with plt.rc_context(style("normal", venue="icml", column="half")):
        _save_lines(mpl_dir=mpl_dir, data=data)
        _save_heatmap(mpl_dir=mpl_dir, data=data)
        _save_bars(mpl_dir=mpl_dir)
        _save_scatter(mpl_dir=mpl_dir, data=data)
        _save_boxplots(mpl_dir=mpl_dir, data=data)
        _save_interval(mpl_dir=mpl_dir, data=data)
        _save_log(mpl_dir=mpl_dir, data=data)
        _save_histogram(mpl_dir=mpl_dir, data=data)

    with plt.rc_context(style("normal", venue="icml", column="full", rows=2, cols=2)):
        _save_group(mpl_dir=mpl_dir, data=data)


def _new_half_axis() -> tuple[Figure, Axes]:
    return plt.subplots(figsize=(HALF_WIDTH_IN, HALF_HEIGHT_IN))


def _save_lines(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    xs = data["xs"]
    lines = data["lines"]
    figure, axis = _new_half_axis()

    for key, label, _, _ in LINE_SERIES:
        ys, yerr = lines[key]
        axis.errorbar(xs, ys, yerr=yerr, marker="o", capsize=0.0, label=label)

    axis.set_xlim(0.0, 10.0)
    axis.set_ylim(0.35, 0.95)
    axis.set_xlabel("budget")
    axis.set_ylabel("accuracy")
    axis.legend(loc="best")
    finish(axis)
    _save_figure(figure=figure, path=mpl_dir / "lines-errorbars.pdf")


def _save_heatmap(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    xs, ys, values = data["heatmap"]
    figure, axis = _new_half_axis()
    image = axis.imshow(
        values,
        origin="lower",
        extent=(-0.5, len(xs) - 0.5, -0.5, len(ys) - 0.5),
        aspect="auto",
        vmin=0.0,
        vmax=1.2,
    )
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_ticks([0.0, 0.4, 0.8, 1.2])
    axis.set_xlabel("width")
    axis.set_ylabel("depth")
    axis.set_xticks(xs)
    axis.set_yticks(ys)
    _save_figure(figure=figure, path=mpl_dir / "heatmap.pdf")


def _save_bars(*, mpl_dir: Path) -> None:
    figure, axis = _new_half_axis()
    centers = [1, 2, 3, 4, 5]
    width = 0.22
    shifts = (-width, 0.0, width)

    for index, (_, label, values) in enumerate(BAR_SERIES):
        positions = [center + shifts[index] for center in centers]
        axis.bar(positions, values, width=width, label=label)

    axis.set_xlim(0.45, 5.55)
    axis.set_ylim(0.0, 1.0)
    axis.set_xticks(centers, ["A", "B", "C", "D", "E"])
    axis.set_ylabel("score")
    axis.legend(loc="best")
    finish(axis)
    _save_figure(figure=figure, path=mpl_dir / "bars.pdf")


def _save_scatter(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    xs, ys, scores = data["scatter"]
    figure, axis = _new_half_axis()
    points = axis.scatter(
        xs,
        ys,
        c=scores,
        s=18.0,
        edgecolors="none",
        vmin=0.0,
        vmax=0.9,
    )
    colorbar = figure.colorbar(points, ax=axis)
    colorbar.set_ticks([0.0, 0.3, 0.6, 0.9])
    axis.set_xlim(0.0, 5.0)
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel("rank")
    axis.set_ylabel("utility")
    _save_figure(figure=figure, path=mpl_dir / "scatter.pdf")


def _save_boxplots(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    boxes = data["boxes"]
    figure, axis = _new_half_axis()
    axis.boxplot(
        [boxes[key] for key, _ in BOX_SERIES],
        positions=[1, 2, 3, 4],
        widths=0.55,
        patch_artist=True,
        showfliers=False,
    )
    axis.set_ylim(0.2, 0.9)
    axis.set_xticks([1, 2, 3, 4], [label for _, label in BOX_SERIES])
    axis.set_ylabel("calibration")
    _save_figure(figure=figure, path=mpl_dir / "boxplots.pdf")


def _save_interval(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    xs, ys, lower, upper = data["interval"]
    figure, axis = _new_half_axis()
    axis.fill_between(xs, lower, upper, alpha=0.18)
    axis.plot(xs, ys, label="mean")
    axis.set_xlim(0.0, 6.0)
    axis.set_ylim(0.0, 0.9)
    axis.set_xlabel("time")
    axis.set_ylabel("risk")
    axis.legend(loc="best")
    finish(axis)
    _save_figure(figure=figure, path=mpl_dir / "interval.pdf")


def _save_log(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    log_data = data["log"]
    figure, axis = _new_half_axis()

    for key, label in (("train", "train"), ("valid", "validation")):
        xs, ys, yerr = log_data[key]
        axis.errorbar(xs, ys, yerr=yerr, marker="o", capsize=0.0, label=label)

    axis.set_yscale("log")
    axis.set_xlim(0.0, 8.0)
    axis.set_ylim(0.01, 1.1)
    axis.set_xlabel("epoch")
    axis.set_ylabel("loss")
    axis.legend(loc="best")
    finish(axis)
    _save_figure(figure=figure, path=mpl_dir / "log-error.pdf")


def _save_histogram(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    centers, counts = data["histogram"]
    figure, axis = _new_half_axis()
    axis.bar(centers, counts, width=0.34)
    axis.set_xlim(-2.8, 2.8)
    axis.set_ylim(0.0, 1.4)
    axis.set_xlabel("margin")
    axis.set_ylabel("density")
    _save_figure(figure=figure, path=mpl_dir / "histogram.pdf")


def _save_group(*, mpl_dir: Path, data: dict[str, Any]) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(FULL_WIDTH_IN, FULL_GROUP_HEIGHT_IN))
    line_axis, scatter_axis, bar_axis, interval_axis = axes.flat
    xs = data["xs"]
    lines = data["lines"]
    scatter = data["scatter"]
    interval = data["interval"]

    for key, label, _, _ in LINE_SERIES[:2]:
        ys, _ = lines[key]
        line_axis.plot(xs, ys, marker="o", label=label)

    line_axis.set_title("curves")
    line_axis.set_xlabel("budget")
    line_axis.set_ylabel("accuracy")
    line_axis.legend(loc="best")
    finish(line_axis)

    scatter_axis.scatter(
        scatter[0],
        scatter[1],
        c=scatter[2],
        s=18.0,
        edgecolors="none",
        vmin=0.0,
        vmax=0.9,
    )
    scatter_axis.set_title("scatter")
    scatter_axis.set_xlabel("rank")

    for index, (_, label, values) in enumerate(BAR_SERIES[:2]):
        shift = -0.12 if index == 0 else 0.12
        positions = [center + shift for center in [1, 2, 3, 4, 5]]
        bar_axis.bar(positions, values, width=0.22, label=label)

    bar_axis.set_title("bars")
    bar_axis.set_xticks([1, 2, 3, 4, 5], ["A", "B", "C", "D", "E"])
    bar_axis.set_ylim(0.0, 1.0)
    bar_axis.legend(loc="best")
    finish(bar_axis)

    interval_axis.fill_between(interval[0], interval[2], interval[3], alpha=0.18)
    interval_axis.plot(interval[0], interval[1])
    interval_axis.set_title("interval")
    interval_axis.set_xlabel("time")
    interval_axis.set_ylim(0.0, 0.9)
    _save_figure(figure=figure, path=mpl_dir / "group-2x2.pdf")


def _save_figure(*, figure: Figure, path: Path) -> None:
    figure.savefig(path)
    plt.close(figure)


def main() -> None:
    """Render the comparison assets from the command line."""
    render_comparison(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
