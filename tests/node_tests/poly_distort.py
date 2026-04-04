import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_zero_coefficients():
    """All coefficients zero should return output approximately equal to input."""
    from backend.nodes.poly_distort import PolynomialDistortion

    node = PolynomialDistortion()
    field = make_field(shape=(64, 64))
    result, = node.process(field, k1_x=0.0, k1_y=0.0, k2_x=0.0, k2_y=0.0, k3_x=0.0, k3_y=0.0)
    assert np.allclose(result.data, field.data, atol=1e-10)


def test_nonzero_distortion():
    """Non-zero k1_x should preserve shape but change values."""
    from backend.nodes.poly_distort import PolynomialDistortion

    node = PolynomialDistortion()
    field = make_field(shape=(64, 64))
    result, = node.process(field, k1_x=0.1, k1_y=0.0, k2_x=0.0, k2_y=0.0, k3_x=0.0, k3_y=0.0)
    assert result.data.shape == field.data.shape
    assert not np.allclose(result.data, field.data)


def test_shape_preserved():
    """Output shape must equal input shape."""
    from backend.nodes.poly_distort import PolynomialDistortion

    node = PolynomialDistortion()
    field = make_field(shape=(32, 48))
    result, = node.process(field, k1_x=0.05, k1_y=0.05, k2_x=0.01, k2_y=0.01, k3_x=0.0, k3_y=0.0)
    assert result.data.shape == (32, 48)
