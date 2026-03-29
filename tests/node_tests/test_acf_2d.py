import numpy as np
from backend.data_types import DataField


def test_acf():
    from backend.nodes.acf_2d import ACF2D

    node = ACF2D()
    data = np.array([
        [1.0, 2.0, 3.0, 4.0],
        [5.0, 6.0, 7.0, 8.0],
        [2.0, 1.0, 0.0, -1.0],
        [0.0, 1.0, 2.0, 3.0],
    ], dtype=np.float64)
    field = DataField(data=data, xreal=8.0, yreal=4.0, si_unit_xy="nm", si_unit_z="V")

    acf, = node.process(field, level="none")
    assert acf.data.shape == (3, 3)
    assert acf.domain == "spatial"
    assert acf.si_unit_xy == "nm"
    assert acf.si_unit_z == "V^2"
    assert np.isclose(acf.xreal, 6.0)
    assert np.isclose(acf.yreal, 3.0)
    assert np.isclose(acf.xoff, -3.0)
    assert np.isclose(acf.yoff, -1.5)

    expected = np.zeros((3, 3), dtype=np.float64)
    for iy, dy in enumerate(range(-1, 2)):
        for ix, dx in enumerate(range(-1, 2)):
            y0a = max(0, dy)
            y1a = min(data.shape[0], data.shape[0] + dy)
            x0a = max(0, dx)
            x1a = min(data.shape[1], data.shape[1] + dx)
            lhs = data[y0a:y1a, x0a:x1a]
            rhs = data[y0a - dy:y1a - dy, x0a - dx:x1a - dx]
            expected[iy, ix] = float(np.mean(lhs * rhs))

    assert np.allclose(acf.data, expected)
    assert np.allclose(acf.data, acf.data[::-1, ::-1])
