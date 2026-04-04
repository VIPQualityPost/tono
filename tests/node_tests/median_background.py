import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_median_background_subtracted():
    from backend.nodes.median_background import MedianBackground

    node = MedianBackground()
    # Tilted surface with features
    yy, xx = np.mgrid[:64, :64]
    data = 0.01 * xx + 0.02 * yy  # tilt
    field = make_field(data=data)
    result, = node.process(field, 20, "subtracted")
    assert result.data.shape == (64, 64)
    # Background-subtracted should have near-zero mean
    assert abs(result.data.mean()) < abs(data.mean())


def test_median_background_output():
    from backend.nodes.median_background import MedianBackground

    node = MedianBackground()
    field = make_field(shape=(32, 32))
    result, = node.process(field, 10, "background")
    assert result.data.shape == (32, 32)


def test_median_background_flat_field():
    from backend.nodes.median_background import MedianBackground

    node = MedianBackground()
    field = make_field(data=np.ones((32, 32)) * 3.0)
    result, = node.process(field, 10, "subtracted")
    assert np.allclose(result.data, 0.0, atol=1e-10)
