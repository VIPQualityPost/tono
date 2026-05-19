import numpy as np
from tests.node_tests._shared import make_field


def test_zero_mean():
    from backend.nodes.zero_value import ZeroMean

    node = ZeroMean()
    data = np.random.default_rng(42).standard_normal((64, 64)) + 100.0
    field = make_field(data=data)
    (result,) = node.process(field)
    assert result.data.shape == field.data.shape
    assert abs(result.data.mean()) < 1e-10


def test_zero_mean_preserves_variation():
    from backend.nodes.zero_value import ZeroMean

    node = ZeroMean()
    data = np.random.default_rng(7).standard_normal((32, 32)) + 50.0
    field = make_field(data=data)
    (result,) = node.process(field)
    assert np.allclose(result.data - result.data.mean(), data - data.mean())


def test_zero_maximum():
    from backend.nodes.zero_value import ZeroMaximum

    node = ZeroMaximum()
    data = np.random.default_rng(42).standard_normal((64, 64)) + 100.0
    field = make_field(data=data)
    (result,) = node.process(field)
    assert result.data.shape == field.data.shape
    assert abs(result.data.max()) < 1e-10
    assert result.data.min() < 0


def test_zero_maximum_preserves_differences():
    from backend.nodes.zero_value import ZeroMaximum

    node = ZeroMaximum()
    data = np.array([[1.0, 3.0], [2.0, 5.0]])
    field = make_field(data=data)
    (result,) = node.process(field)
    expected = data - 5.0
    assert np.allclose(result.data, expected)
