import numpy as np
from tests.node_tests._shared import make_field


def test_fix_zero():
    from backend.nodes.fix_zero import FixZero
    node = FixZero()
    field = make_field(data=np.array([[10, 20], [30, 40]], dtype=np.float64))

    result_min, = node.process(field, method="min")
    assert result_min.data.min() == 0.0
    assert result_min.data.max() == 30.0

    result_mean, = node.process(field, method="mean")
    assert abs(result_mean.data.mean()) < 1e-10

    result_median, = node.process(field, method="median")
    assert abs(np.median(result_median.data)) < 1e-10


def test_fix_zero_unknown_method():
    from backend.nodes.fix_zero import FixZero
    import pytest
    node = FixZero()
    field = make_field(data=np.array([[1.0, 2.0], [3.0, 4.0]]))
    try:
        node.process(field, method="invalid_method")
        assert False, "Expected ValueError"
    except ValueError:
        pass
