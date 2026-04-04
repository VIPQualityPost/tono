import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_erosion_le_original():
    """Erosion (local minimum) values should be <= original at every pixel."""
    from backend.nodes.filter_rank import RankFilter

    node = RankFilter()
    field = make_field(shape=(64, 64))
    result, = node.process(field, operation="erosion", radius=2, percentile=50.0)
    assert np.all(result.data <= field.data + 1e-12)


def test_dilation_ge_original():
    """Dilation (local maximum) values should be >= original at every pixel."""
    from backend.nodes.filter_rank import RankFilter

    node = RankFilter()
    field = make_field(shape=(64, 64))
    result, = node.process(field, operation="dilation", radius=2, percentile=50.0)
    assert np.all(result.data >= field.data - 1e-12)


def test_median_shape():
    """Median output should have the same shape as input."""
    from backend.nodes.filter_rank import RankFilter

    node = RankFilter()
    field = make_field(shape=(64, 64))
    result, = node.process(field, operation="median", radius=3, percentile=50.0)
    assert result.data.shape == field.data.shape


def test_percentile_operation():
    """Percentile at 50.0 should approximate the median result."""
    from backend.nodes.filter_rank import RankFilter

    node = RankFilter()
    field = make_field(shape=(64, 64))
    median_result, = node.process(field, operation="median", radius=2, percentile=50.0)
    percentile_result, = node.process(field, operation="percentile", radius=2, percentile=50.0)
    assert np.allclose(median_result.data, percentile_result.data, atol=1e-10)
