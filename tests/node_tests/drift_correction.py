import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_drift_correction_flat():
    from backend.nodes.drift_correction import DriftCorrection

    node = DriftCorrection()
    field = make_field(data=np.zeros((32, 32)))
    result, drift = node.process(field, "previous_row", "horizontal")
    assert result.data.shape == (32, 32)
    assert np.allclose(result.data, 0.0, atol=1e-10)
    # Drift table: max/mean/RMS in px plus max in physical units.
    assert len(drift) == 4
    assert [row["quantity"] for row in drift] == [
        "Max drift (px)", "Mean |drift| (px)", "RMS drift (px)", "Max drift",
    ]
    assert all(set(row) == {"quantity", "value", "unit"} for row in drift)
    assert [row["unit"] for row in drift] == ["px", "px", "px", field.si_unit_xy]
    # The reported stats are magnitudes — never negative.
    assert all(row["value"] >= 0.0 for row in drift)


def test_drift_correction_preserves_shape():
    from backend.nodes.drift_correction import DriftCorrection

    node = DriftCorrection()
    field = make_field(shape=(48, 64))
    for ref in ("previous_row", "mean_row"):
        for direction in ("horizontal", "vertical"):
            result, drift = node.process(field, ref, direction)
            assert result.data.shape == (48, 64)
            assert len(drift) == 4


def test_drift_correction_reduces_drift():
    """A field with artificial row-by-row drift should have less variance after correction."""
    from backend.nodes.drift_correction import DriftCorrection

    node = DriftCorrection()
    rng = np.random.default_rng(42)
    base = rng.standard_normal((32, 64))
    # Add artificial drift: shift each row by cumulative offset
    drifted = base.copy()
    for i in range(1, 32):
        drifted[i] = np.roll(base[i], i)

    field = make_field(data=drifted)
    result, drift = node.process(field, "previous_row", "horizontal")
    # The corrected field should have lower inter-row variance
    row_means_before = np.var(np.diff(drifted, axis=0))
    row_means_after = np.var(np.diff(result.data, axis=0))
    assert row_means_after <= row_means_before
    # The estimated drift is reported as a standard record table.
    assert all(set(row) == {"quantity", "value", "unit"} for row in drift)
    assert len(drift) == 4


def test_drift_correction_mean_row_reference():
    from backend.nodes.drift_correction import DriftCorrection

    node = DriftCorrection()
    field = make_field(shape=(32, 32))
    result, drift = node.process(field, "mean_row", "horizontal")
    assert result.data.shape == (32, 32)
    assert len(drift) == 4
