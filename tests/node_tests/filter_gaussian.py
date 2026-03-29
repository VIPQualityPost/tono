import numpy as np
from tests.node_tests._shared import make_field


def test_gaussian_filter():
    from backend.nodes.filter_gaussian import GaussianFilter
    node = GaussianFilter()
    field = make_field()

    result, = node.process(field, sigma=2.0)
    assert result.data.shape == field.data.shape
    assert result.xreal == field.xreal
    assert result.si_unit_z == field.si_unit_z
    assert result.data.std() < field.data.std()
    result_tiny, = node.process(field, sigma=0.01)
    assert np.allclose(result_tiny.data, field.data, atol=1e-6)
