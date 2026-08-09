import numpy as np
import pytest
from backend.data_types import DataField
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
    result, background = node.process(field, 30.0, 1)
    assert result.data.shape == (64, 64)
    # Features should remain raised, base should be flatter
    assert result.data[25, 25] > result.data[0, 0]
    # Background output is the fitted base, same shape as the field
    assert isinstance(background, DataField)
    assert background.data.shape == field.data.shape
    # The fitted base tracks the tilted plane (features excluded from the fit)
    assert np.allclose(background.data, base_tilt, atol=1e-8)


def test_flatten_base_preserves_shape():
    from backend.nodes.flatten_base import FlattenBase

    node = FlattenBase()
    field = make_field(shape=(48, 64))
    result, background = node.process(field, 30.0, 2)
    assert result.data.shape == (48, 64)
    assert isinstance(background, DataField)
    assert background.data.shape == (48, 64)


def test_flatten_base_flat_surface():
    from backend.nodes.flatten_base import FlattenBase

    node = FlattenBase()
    field = make_field(data=np.ones((32, 32)) * 5.0)
    result, background = node.process(field, 50.0, 0)
    # All pixels are the same, subtracting mean gives zero
    assert np.allclose(result.data, 0.0, atol=1e-10)
    # Background equals the constant level that was subtracted
    assert isinstance(background, DataField)
    assert background.data.shape == (32, 32)
    assert np.allclose(background.data, 5.0, atol=1e-10)
