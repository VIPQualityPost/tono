import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_add_subtract_roundtrip():
    """Adding then subtracting the same tilt should recover the original."""
    from backend.nodes.tilt import Tilt

    node = Tilt()
    field = make_field(shape=(64, 64))
    tilted, = node.process(field, slope_x=1000.0, slope_y=500.0, mode="add")
    recovered, = node.process(tilted, slope_x=1000.0, slope_y=500.0, mode="subtract")
    assert np.allclose(recovered.data, field.data, atol=1e-10)


def test_add_tilt_changes_data():
    """Adding a non-zero tilt should change the data."""
    from backend.nodes.tilt import Tilt

    node = Tilt()
    field = make_field(shape=(64, 64))
    result, = node.process(field, slope_x=1000.0, slope_y=0.0, mode="add")
    assert not np.allclose(result.data, field.data)


def test_zero_slope():
    """Zero slopes in add mode should leave data unchanged."""
    from backend.nodes.tilt import Tilt

    node = Tilt()
    field = make_field(shape=(64, 64))
    result, = node.process(field, slope_x=0.0, slope_y=0.0, mode="add")
    assert np.allclose(result.data, field.data, atol=1e-10)
