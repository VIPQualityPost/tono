import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_shape_increase():
    """32x32 + top=5, bottom=5, left=10, right=10 should give 42x52."""
    from backend.nodes.extend_pad import ExtendPad

    node = ExtendPad()
    field = make_field(shape=(32, 32))
    result, = node.process(field, top=5, bottom=5, left=10, right=10, method="mirror")
    assert result.data.shape == (42, 52)


def test_zero_pad():
    """Zero padding should fill borders with zeros."""
    from backend.nodes.extend_pad import ExtendPad

    node = ExtendPad()
    data = np.ones((16, 16), dtype=np.float64) * 7.0
    field = make_field(data=data)
    result, = node.process(field, top=2, bottom=2, left=2, right=2, method="zero")
    assert result.data.shape == (20, 20)
    # Top border rows should be zero
    assert np.allclose(result.data[:2, :], 0.0)
    # Bottom border rows should be zero
    assert np.allclose(result.data[-2:, :], 0.0)
    # Left border columns should be zero
    assert np.allclose(result.data[:, :2], 0.0)
    # Right border columns should be zero
    assert np.allclose(result.data[:, -2:], 0.0)


def test_mirror_pad():
    """Mirror padding should produce the correct output shape."""
    from backend.nodes.extend_pad import ExtendPad

    node = ExtendPad()
    field = make_field(shape=(32, 32))
    result, = node.process(field, top=4, bottom=4, left=8, right=8, method="mirror")
    assert result.data.shape == (40, 48)
