import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_shape_reduction():
    """64x64 with bin_size=2 should produce 32x32."""
    from backend.nodes.pixel_binning import PixelBinning

    node = PixelBinning()
    field = make_field(shape=(64, 64))
    result, = node.process(field, bin_size=2, method="mean")
    assert result.data.shape == (32, 32)


def test_mean_uniform():
    """Uniform field of value 5.0 with mean binning should keep all values at 5.0."""
    from backend.nodes.pixel_binning import PixelBinning

    node = PixelBinning()
    data = np.full((64, 64), 5.0, dtype=np.float64)
    field = make_field(data=data)
    result, = node.process(field, bin_size=2, method="mean")
    assert np.allclose(result.data, 5.0)


def test_sum_doubles():
    """Uniform field of 1.0 with bin_size=2 and sum should give 4.0 everywhere."""
    from backend.nodes.pixel_binning import PixelBinning

    node = PixelBinning()
    data = np.ones((64, 64), dtype=np.float64)
    field = make_field(data=data)
    result, = node.process(field, bin_size=2, method="sum")
    assert np.allclose(result.data, 4.0)
