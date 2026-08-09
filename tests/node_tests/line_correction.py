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


def test_line_correction_methods():
    from backend.nodes.line_correction import LineCorrection
    from tests.node_tests._shared import make_field

    node = LineCorrection()

    rows, cols = 64, 80
    rng = np.random.default_rng(7)
    signal = rng.standard_normal((rows, cols)) * 0.1
    row_offsets = rng.standard_normal(rows) * 2.0
    data = signal + row_offsets[:, None]
    field = make_field(data=data)

    # median_diff
    c, b, s = node.process(field, method="median_diff", direction="horizontal",
                           masking="ignore", trim_fraction=0.05, polynomial_degree=1)
    assert np.allclose(c.data + b.data, field.data)
    assert len(s) == rows

    # trimmed_mean
    c, b, s = node.process(field, method="trimmed_mean", direction="horizontal",
                           masking="ignore", trim_fraction=0.2, polynomial_degree=1)
    assert np.allclose(c.data + b.data, field.data)

    # trimmed_diff
    c, b, s = node.process(field, method="trimmed_diff", direction="horizontal",
                           masking="ignore", trim_fraction=0.2, polynomial_degree=1)
    assert np.allclose(c.data + b.data, field.data)

    # step
    c, b, s = node.process(field, method="step", direction="horizontal",
                           masking="ignore", trim_fraction=0.05, polynomial_degree=1)
    assert np.allclose(c.data + b.data, field.data)
    assert len(s) == rows


def test_line_correction_vertical():
    from backend.nodes.line_correction import LineCorrection
    from tests.node_tests._shared import make_field

    node = LineCorrection()

    rows, cols = 48, 64
    col_offsets = np.random.default_rng(3).standard_normal(cols) * 1.5
    data = np.random.default_rng(3).standard_normal((rows, cols)) * 0.1 + col_offsets[None, :]
    field = make_field(data=data)

    c, b, s = node.process(field, method="median", direction="vertical",
                           masking="ignore", trim_fraction=0.05, polynomial_degree=1)
    assert c.data.shape == field.data.shape
    assert np.allclose(c.data + b.data, field.data)
    # vertical shift line length = number of columns
    assert len(s) == cols
    assert s.x_axis is not None
    assert np.isclose(s.x_axis[-1], field.xreal)


def test_line_correction_with_mask():
    from backend.nodes.line_correction import LineCorrection
    from tests.node_tests._shared import make_field

    node = LineCorrection()

    rows, cols = 32, 48
    data = np.random.default_rng(9).standard_normal((rows, cols)) * 0.1
    row_offsets = np.linspace(0, 3.0, rows)
    data += row_offsets[:, None]
    field = make_field(data=data)

    # mask covers right half
    mask = np.zeros((rows, cols), dtype=np.uint8)
    mask[:, cols // 2:] = 255

    c_excl, b_excl, _ = node.process(field, method="median", direction="horizontal",
                                      masking="exclude", trim_fraction=0.05,
                                      polynomial_degree=1, mask=mask)
    assert np.allclose(c_excl.data + b_excl.data, field.data)

    c_incl, b_incl, _ = node.process(field, method="median", direction="horizontal",
                                      masking="include", trim_fraction=0.05,
                                      polynomial_degree=1, mask=mask)
    assert np.allclose(c_incl.data + b_incl.data, field.data)


def test_line_correction_modus():
    from backend.nodes.line_correction import LineCorrection
    from tests.node_tests._shared import make_field

    node = LineCorrection()

    rows, cols = 64, 128
    rng = np.random.default_rng(21)
    x = np.linspace(-1.0, 1.0, cols)
    # Flat plateau with a weak non-modal component: the modus of each row is
    # the plateau value plus its offset.
    base = 0.02 * np.sin(3.0 * np.pi * x) + rng.standard_normal((rows, cols)) * 0.01
    row_offsets = np.array([-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5])[
        np.arange(rows) % 7]
    data = base + row_offsets[:, None]
    field = make_field(data=data)

    corrected, background, shifts = node.process(
        field, method="modus", direction="horizontal",
        masking="ignore", trim_fraction=0.05, polynomial_degree=1,
    )
    expected = row_offsets - row_offsets.mean()
    assert corrected.data.shape == field.data.shape
    assert np.allclose(corrected.data + background.data, field.data)
    assert len(shifts) == rows
    assert np.max(np.abs(shifts.data - expected)) < 0.05
    assert corrected.data.mean(axis=1).std() < field.data.mean(axis=1).std() * 0.05


def test_line_correction_matching():
    from backend.nodes.line_correction import LineCorrection
    from tests.node_tests._shared import make_field

    node = LineCorrection()

    rows, cols = 64, 128
    rng = np.random.default_rng(33)
    x = np.linspace(0.0, 1.0, cols)
    # Rich row structure so local slopes vary; rows are identical up to an
    # integer-valued offset (plus tiny noise so the weight denominator q > 0).
    structure = (
        0.6 * np.sin(7.0 * np.pi * x)
        + 0.3 * np.cos(13.0 * np.pi * x)
        + 0.15 * np.sin(31.0 * np.pi * x)
    )
    row_offsets = 0.5 * np.array([0, 1, 2, 3, 2, 1, 0, -1, -2, -3, -2, -1])[
        np.arange(rows) % 12
    ].astype(np.float64)
    noise = rng.standard_normal((rows, cols)) * 1e-3
    data = structure[None, :] + row_offsets[:, None] + noise
    field = make_field(data=data)

    corrected, background, shifts = node.process(
        field, method="matching", direction="horizontal",
        masking="ignore", trim_fraction=0.05, polynomial_degree=1,
    )
    expected = row_offsets - row_offsets.mean()
    assert corrected.data.shape == field.data.shape
    assert np.allclose(corrected.data + background.data, field.data)
    assert len(shifts) == rows
    assert shifts.x_unit == field.si_unit_xy
    assert shifts.y_unit == field.si_unit_z
    assert np.max(np.abs(shifts.data - expected)) < 0.05
    assert corrected.data.mean(axis=1).std() < field.data.mean(axis=1).std() * 0.05
