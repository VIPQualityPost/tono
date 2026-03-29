import numpy as np
from tests.node_tests._shared import make_field


def test_poly_level():
    from backend.nodes.level_poly import PolyLevelField
    node = PolyLevelField()

    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    background = 50 * x**2 + 30 * y**2 + 10 * x * y
    signal = np.sin(2 * np.pi * 8 * x)
    data = background + signal
    field = make_field(data=data)

    leveled, bg = node.process(field, degree_x=2, degree_y=2)
    assert leveled.data.shape == field.data.shape
    assert bg.data.shape == field.data.shape
    assert np.allclose(leveled.data + bg.data, field.data, atol=1e-10)
    corr = np.corrcoef(leveled.data.ravel(), signal.ravel())[0, 1]
    assert corr > 0.95

    leveled_0, bg_0 = node.process(field, degree_x=0, degree_y=0)
    assert abs(leveled_0.data.mean()) < 1e-10
