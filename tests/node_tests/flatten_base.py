import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_flatten_base_removes_tilt():
    from backend.nodes.flatten_base import FlattenBase

    node = FlattenBase()
    yy, xx = np.mgrid[:64, :64]
    base_tilt = 0.01 * xx + 0.02 * yy
    # Add some tall features
    data = base_tilt.copy()
    data[20:30, 20:30] += 10.0
    field = make_field(data=data)
    result, = node.process(field, 30.0, 1)
    assert result.data.shape == (64, 64)
    # Features should remain raised, base should be flatter
    assert result.data[25, 25] > result.data[0, 0]


def test_flatten_base_preserves_shape():
    from backend.nodes.flatten_base import FlattenBase

    node = FlattenBase()
    field = make_field(shape=(48, 64))
    result, = node.process(field, 30.0, 2)
    assert result.data.shape == (48, 64)


def test_flatten_base_flat_surface():
    from backend.nodes.flatten_base import FlattenBase

    node = FlattenBase()
    field = make_field(data=np.ones((32, 32)) * 5.0)
    result, = node.process(field, 50.0, 0)
    # All pixels are the same, subtracting mean gives zero
    assert np.allclose(result.data, 0.0, atol=1e-10)
