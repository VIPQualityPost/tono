import numpy as np
import pytest
from tests.node_tests._shared import make_field


@pytest.fixture(scope="module")
def node():
    from backend.nodes.mfm_lift_estimate import MFMLiftEstimate

    return MFMLiftEstimate()


@pytest.fixture(scope="module")
def oscillatory_field():
    """A field with a few well-defined spatial frequencies, for which the
    lift-shift transfer function is perfectly identifiable."""
    x = np.linspace(0.0, 1.28e-6, 64, endpoint=False)
    X, Y = np.meshgrid(x, x)
    data = np.sin(2 * np.pi * 8.0 * X / 1.28e-6) + 0.5 * np.cos(
        2 * np.pi * 6.0 * Y / 1.28e-6
    )
    return make_field(data=data, shape=(64, 64), xreal=1.28e-6, yreal=1.28e-6)


def test_recovers_known_shift(node, oscillatory_field):
    """Shift the field by a known +15 nm and check the estimate recovers it
    (the second image is the first one measured at a larger lift height)."""
    from backend.nodes.mfm_lift_shift import _mfm_shift_z

    shifted = oscillatory_field.replace(
        data=_mfm_shift_z(oscillatory_field.data, oscillatory_field.xreal,
                          oscillatory_field.yreal, 15e-9)
    )
    residual, table = node.process(oscillatory_field, shifted, 0.0, 50e-9)
    rows = {r["quantity"]: (r["value"], r["unit"]) for r in table}
    value, unit = rows["Estimated lift shift"]
    assert unit == "m"
    assert abs(value - 15e-9) < 1e-9
    assert rows["Search range from"] == (0.0, "m")
    assert rows["Search range to"] == (50e-9, "m")
    # Sharpening a blurred image by the estimate reproduces the reference:
    # the residual field (shifted input minus comparison) must be tiny.
    assert residual.data.shape == oscillatory_field.data.shape
    assert np.abs(residual.data).max() < 1e-10


def test_identical_fields_estimate_zero(node, oscillatory_field):
    residual, table = node.process(oscillatory_field, oscillatory_field, -20e-9, 20e-9)
    value = {r["quantity"]: r["value"] for r in table}["Estimated lift shift"]
    assert abs(value) < 1e-10
    assert np.allclose(residual.data, 0.0, atol=1e-12)


def test_reversed_search_range_is_ordered(node, oscillatory_field):
    """start > stop must not break the search: range is ordered internally."""
    from backend.nodes.mfm_lift_shift import _mfm_shift_z

    shifted = oscillatory_field.replace(
        data=_mfm_shift_z(oscillatory_field.data, oscillatory_field.xreal,
                          oscillatory_field.yreal, 12e-9)
    )
    _, table = node.process(oscillatory_field, shifted, 50e-9, 0.0)
    rows = {r["quantity"]: (r["value"], r["unit"]) for r in table}
    assert abs(rows["Estimated lift shift"][0] - 12e-9) < 1e-9
    assert rows["Search range from"] == (0.0, "m")
    assert rows["Search range to"] == (50e-9, "m")


def test_negative_shift_recovered(node, oscillatory_field):
    """A comparison image measured at a smaller lift height (sharpened) gives
    a negative estimate."""
    from backend.nodes.mfm_lift_shift import _mfm_shift_z

    sharp = oscillatory_field.replace(
        data=_mfm_shift_z(oscillatory_field.data, oscillatory_field.xreal,
                          oscillatory_field.yreal, -8e-9)
    )
    _, table = node.process(oscillatory_field, sharp, -30e-9, 30e-9)
    value = {r["quantity"]: r["value"] for r in table}["Estimated lift shift"]
    assert abs(value - (-8e-9)) < 1e-9


def test_resolution_mismatch_raises(node, oscillatory_field):
    other = make_field(shape=(32, 64), xreal=1.28e-6, yreal=1.28e-6)
    with pytest.raises(ValueError):
        node.process(oscillatory_field, other, 0.0, 50e-9)
