"""Tests for the preview script."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load_preview() -> ModuleType:
    script_path = Path(__file__).parents[1] / "preview.py"
    spec = importlib.util.spec_from_file_location("preview", script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_preview_script_renders_expected_files(tmp_path: Path) -> None:
    preview = load_preview()

    preview.render_previews(tmp_path)

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "layouts",
        "plot_types",
        "themes",
    ]
    assert sorted(
        path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.pdf")
    ) == [
        "layouts/layout_iclr-full_2x1.pdf",
        "layouts/layout_icml-full_1x2.pdf",
        "layouts/layout_icml-half_1x1.pdf",
        "layouts/layout_neurips-full_2x2.pdf",
        "plot_types/bar_iteration_counts.pdf",
        "plot_types/contour_optimization_path.pdf",
        "plot_types/line_convergence.pdf",
        "plot_types/surface_quadratic.pdf",
        "themes/talk_frappe_overrides.pdf",
        "themes/theme_frappe.pdf",
        "themes/theme_latte.pdf",
        "themes/theme_macchiato.pdf",
        "themes/theme_mocha.pdf",
        "themes/theme_normal.pdf",
    ]

    for path in tmp_path.rglob("*.pdf"):
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 0


def test_convergence_curves_match_quadratic_gap() -> None:
    preview = load_preview()

    iterations, curves = preview._convergence_curves(condition_number=4.0)

    assert iterations[:3] == [0.0, 1.0, 2.0]
    assert len(curves) == 4
    assert [values[0] for values in curves] == [1.0, 1.0, 1.0, 1.0]
    assert curves[1][1] == pytest.approx(0.353125)
    assert curves[3][-1] < curves[0][-1]


def test_layout_diagnostics_are_quadratic_quantities() -> None:
    preview = load_preview()

    fractions, gaps = preview._step_sensitivity_points(
        condition_number=4.0,
        iteration=2.0,
    )
    condition_numbers, worst_case_gaps = preview._condition_sensitivity_points(
        step_fraction=0.5,
        iteration=2.0,
    )

    assert fractions[0] == pytest.approx(0.10)
    assert fractions[-1] == pytest.approx(0.95)
    assert gaps[-1] < gaps[0]
    assert condition_numbers == [5.0, 10.0, 20.0, 40.0, 80.0, 160.0]
    assert worst_case_gaps[-1] > worst_case_gaps[0]


def test_plot_type_data_are_quadratic_quantities() -> None:
    preview = load_preview()

    labels, count_groups = preview._iteration_count_bars(step_fraction=1.0)
    x_values, y_values, z_values = preview._surface_grid(condition_number=8.0)

    assert labels == ["10", "40", "160"]
    assert count_groups[1][0] > count_groups[0][0]
    assert count_groups[0][2] > count_groups[0][0]
    assert x_values[10, 10] == pytest.approx(0.0)
    assert y_values[10, 10] == pytest.approx(0.0)
    assert z_values[10, 10] == pytest.approx(0.0)
    assert z_values[20, 10] == pytest.approx(4.0)
