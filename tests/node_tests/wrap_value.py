import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_wrap_degrees():
    """Value 400.0 wrapped to 0..360 should give 40.0."""
    from backend.nodes.wrap_value import WrapValue

    node = WrapValue()
    data = np.array([[400.0]], dtype=np.float64)
    field = make_field(data=data)
    result, = node.process(field, range="0_to_360", custom_min=0.0, custom_max=360.0)
    assert np.isclose(result.data[0, 0], 40.0)


def test_wrap_negative():
    """Value -90.0 wrapped to 0..360 should give 270.0."""
    from backend.nodes.wrap_value import WrapValue

    node = WrapValue()
    data = np.array([[-90.0]], dtype=np.float64)
    field = make_field(data=data)
    result, = node.process(field, range="0_to_360", custom_min=0.0, custom_max=360.0)
    assert np.isclose(result.data[0, 0], 270.0)


def test_custom_range():
    """Value 250 with custom range 0..100 should wrap to 50."""
    from backend.nodes.wrap_value import WrapValue

    node = WrapValue()
    data = np.array([[250.0]], dtype=np.float64)
    field = make_field(data=data)
    result, = node.process(field, range="custom", custom_min=0.0, custom_max=100.0)
    assert np.isclose(result.data[0, 0], 50.0)
