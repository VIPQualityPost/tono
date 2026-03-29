import numpy as np
from backend.data_types import LineData
from backend.node_registry import get_node_info
from tests.node_tests._shared import make_field


def test_line_correction():
    from backend.nodes.line_correction import LineCorrection

    node = LineCorrection()
    assert get_node_info("LineCorrection")["category"] == "Level & Correct"

    rows = 96
    cols = 128
    y = np.linspace(0.0, 1.0, rows, dtype=np.float64)
    x = np.linspace(-1.0, 1.0, cols, dtype=np.float64)
    signal = (
        0.15 * np.sin(8.0 * np.pi * x)[None, :]
        + 0.05 * np.cos(4.0 * np.pi * y)[:, None]
    )
    row_offsets = 1.5 * np.sin(3.0 * np.pi * y) + 0.25 * np.cos(7.0 * np.pi * y)
    field = make_field(data=signal + row_offsets[:, None], xreal=2.5e-6, yreal=1.5e-6)

    corrected, background, shifts = node.process(
        field, method="median", direction="horizontal", masking="ignore",
        trim_fraction=0.05, polynomial_degree=1,
    )
    expected_shifts = row_offsets - row_offsets.mean()
    assert corrected.data.shape == field.data.shape
    assert background.data.shape == field.data.shape
    assert np.allclose(corrected.data + background.data, field.data)
    assert isinstance(shifts, LineData)
    assert shifts.x_unit == field.si_unit_xy
    assert shifts.y_unit == field.si_unit_z
    assert np.isclose(shifts.x_axis[0], 0.0)
    assert np.isclose(shifts.x_axis[-1], field.yreal)
    assert np.corrcoef(shifts.data, expected_shifts)[0, 1] > 0.999
    assert corrected.data.mean(axis=1).std() < field.data.mean(axis=1).std() * 0.03

    poly_background = (
        row_offsets[:, None]
        + (0.35 * y - 0.15)[:, None] * x[None, :]
        + (0.10 + 0.05 * y)[:, None] * (x[None, :] ** 2)
    )
    poly_signal = 0.08 * np.sin(10.0 * np.pi * x)[None, :] * (1.0 + 0.15 * np.cos(2.0 * np.pi * y)[:, None])
    poly_field = make_field(data=poly_signal + poly_background)

    leveled, poly_bg, poly_shifts = node.process(
        poly_field, method="polynomial", direction="horizontal", masking="ignore",
        trim_fraction=0.05, polynomial_degree=2,
    )
    assert np.allclose(leveled.data + poly_bg.data, poly_field.data)
    assert np.corrcoef(leveled.data.ravel(), poly_signal.ravel())[0, 1] > 0.995
    assert len(poly_shifts) == rows
