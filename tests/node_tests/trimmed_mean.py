import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_uniform_field():
    """Uniform field should remain approximately the same after filtering."""
    from backend.nodes.trimmed_mean import TrimmedMean

    node = TrimmedMean()
    data = np.full((16, 16), 3.0, dtype=np.float64)
    field = make_field(data=data)
    result, = node.process(field, radius=2, trim_fraction=0.1)
    assert np.allclose(result.data, 3.0, atol=1e-10)


def test_shape_preserved():
    """Output shape should match input shape."""
    from backend.nodes.trimmed_mean import TrimmedMean

    node = TrimmedMean()
    field = make_field(shape=(16, 16))
    result, = node.process(field, radius=2, trim_fraction=0.1)
    assert result.data.shape == (16, 16)


def test_reduces_outliers():
    """A spike in the field should be reduced by the trimmed mean filter."""
    from backend.nodes.trimmed_mean import TrimmedMean

    node = TrimmedMean()
    data = np.zeros((16, 16), dtype=np.float64)
    data[8, 8] = 100.0  # large spike
    field = make_field(data=data)
    result, = node.process(field, radius=2, trim_fraction=0.1)
    # The spike should be significantly reduced
    assert result.data[8, 8] < 50.0
