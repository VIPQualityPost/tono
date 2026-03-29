import numpy as np
from tests.node_tests._shared import make_field


def test_median_filter():
    from backend.nodes.filter_median import MedianFilter
    node = MedianFilter()

    data = np.zeros((64, 64))
    rng = np.random.default_rng(7)
    noise_idx = rng.choice(64 * 64, size=100, replace=False)
    data.ravel()[noise_idx] = 1.0
    field = make_field(data=data)

    result, = node.process(field, size=3)
    assert result.data.shape == field.data.shape
    assert result.data.sum() < field.data.sum()
    result_1, = node.process(field, size=1)
    assert np.array_equal(result_1.data, field.data)
