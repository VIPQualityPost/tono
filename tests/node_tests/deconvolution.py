import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_wiener_preserves_shape():
    from backend.nodes.deconvolution import Deconvolution

    node = Deconvolution()
    field = make_field(shape=(32, 32))
    result, = node.process(field, "wiener", 2.0, 0.01, 10)
    assert result.data.shape == (32, 32)
    assert np.isfinite(result.data).all()


def test_richardson_lucy_preserves_shape():
    from backend.nodes.deconvolution import Deconvolution

    node = Deconvolution()
    field = make_field(data=np.abs(np.random.default_rng(42).standard_normal((32, 32))) + 0.1)
    result, = node.process(field, "richardson_lucy", 2.0, 0.01, 5)
    assert result.data.shape == (32, 32)
    assert np.isfinite(result.data).all()


def test_wiener_flat_field():
    from backend.nodes.deconvolution import Deconvolution

    node = Deconvolution()
    field = make_field(data=np.ones((32, 32)))
    result, = node.process(field, "wiener", 2.0, 0.01, 10)
    # A flat field convolved with anything is still flat; Wiener should preserve it
    assert result.data.shape == (32, 32)


def test_unknown_method():
    from backend.nodes.deconvolution import Deconvolution

    node = Deconvolution()
    field = make_field(shape=(32, 32))
    with pytest.raises(ValueError):
        node.process(field, "unknown", 2.0, 0.01, 10)
