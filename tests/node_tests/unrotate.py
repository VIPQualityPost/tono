import numpy as np
from tests.node_tests._shared import make_field


def test_unrotate_preserves_shape():
    from backend.nodes.unrotate import Unrotate

    node = Unrotate()
    data = np.random.default_rng(42).standard_normal((64, 64))
    field = make_field(data=data)

    (result,) = node.process(field, symmetry="4-fold")
    assert result.data.shape == (64, 64)


def test_unrotate_small_angle():
    from backend.nodes.unrotate import Unrotate, _slope_angle_histogram, _find_dominant_angle

    y, x = np.mgrid[:128, :128].astype(np.float64)
    angle_deg = 3.0
    angle_rad = np.radians(angle_deg)
    data = np.sin(2 * np.pi * (x * np.cos(angle_rad) + y * np.sin(angle_rad)) / 20.0)

    hist = _slope_angle_histogram(data)
    correction = _find_dominant_angle(hist, 4)
    assert abs(np.degrees(correction)) < 10.0


def test_unrotate_no_rotation_passthrough():
    from backend.nodes.unrotate import Unrotate

    node = Unrotate()
    y, x = np.mgrid[:64, :64].astype(np.float64)
    data = np.sin(2 * np.pi * x / 16.0)
    field = make_field(data=data)

    (result,) = node.process(field, symmetry="4-fold")
    assert np.allclose(result.data, data, atol=0.1)


def test_unrotate_symmetry_options():
    from backend.nodes.unrotate import Unrotate

    node = Unrotate()
    data = np.random.default_rng(99).standard_normal((64, 64))
    field = make_field(data=data)

    for sym in ["2-fold", "3-fold", "4-fold", "6-fold"]:
        (result,) = node.process(field, symmetry=sym)
        assert result.data.shape == (64, 64)
