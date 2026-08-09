import numpy as np
import pytest
from tests.node_tests._shared import make_field


def run_tip_shape(field, feature_type="edge", feature_radius=100e-9, n_points=100):
    from backend.nodes.tip_shape_estimate import TipShapeEstimate
    node = TipShapeEstimate()
    tip_shape, parameters = node.process(
        field=field,
        feature_type=feature_type,
        feature_radius=feature_radius,
        n_points=n_points,
    )
    return tip_shape, parameters


# ── Output shape and type ────────────────────────────────────────────────────

def test_output_shape():
    """tip_shape must be a 2D DataField."""
    from backend.data_types import DataField
    field = make_field(shape=(64, 64), xreal=64e-9, yreal=64e-9)
    tip_shape, _ = run_tip_shape(field, feature_type="edge", n_points=33)
    assert isinstance(tip_shape, DataField)
    assert tip_shape.data.ndim == 2
    assert tip_shape.data.shape[0] == tip_shape.data.shape[1]


# ── Parameters table ─────────────────────────────────────────────────────────

def test_parameters_table():
    """parameters must be a RecordTable containing a tip_radius entry."""
    from backend.data_types import RecordTable
    field = make_field(shape=(64, 64), xreal=64e-9, yreal=64e-9)
    _, parameters = run_tip_shape(field, feature_type="edge", n_points=33)
    assert isinstance(parameters, RecordTable)
    quantities = {row["quantity"] for row in parameters}
    assert "tip_radius" in quantities


# ── Tip apex is maximum ──────────────────────────────────────────────────────

def test_tip_apex_is_maximum():
    """The center of the tip shape should be the highest point."""
    field = make_field(shape=(64, 64), xreal=64e-9, yreal=64e-9)
    tip_shape, _ = run_tip_shape(field, feature_type="edge", n_points=33)
    n = tip_shape.data.shape[0]
    ci = n // 2
    assert tip_shape.data[ci, ci] == pytest.approx(tip_shape.data.max(), abs=1e-20)


# ── Sphere feature produces valid estimate ───────────────────────────────────

def test_sphere_feature():
    """Using a synthetic sphere as input produces a valid tip estimate."""
    from backend.data_types import DataField

    # Create a synthetic sphere on a 64x64 grid.
    R = 100e-9  # sphere radius
    n = 64
    pixel_size = 10e-9
    xreal = n * pixel_size
    Y, X = np.mgrid[:n, :n]
    r = np.sqrt((X - 32) ** 2 + (Y - 32) ** 2) * pixel_size
    data = np.sqrt(np.maximum(R ** 2 - r ** 2, 0.0))

    field = make_field(data=data, xreal=xreal, yreal=xreal)

    tip_shape, parameters = run_tip_shape(
        field, feature_type="sphere", feature_radius=R, n_points=33,
    )

    # The output must be a valid 2D DataField.
    assert isinstance(tip_shape, DataField)
    assert tip_shape.data.ndim == 2

    # Apex should be the maximum.
    ci = tip_shape.data.shape[0] // 2
    assert tip_shape.data[ci, ci] == pytest.approx(tip_shape.data.max(), abs=1e-20)

    # Parameters should contain tip_radius.
    quantities = {row["quantity"]: row["value"] for row in parameters}
    assert "tip_radius" in quantities
    # The estimated radius must be a positive finite number.
    assert quantities["tip_radius"] > 0
