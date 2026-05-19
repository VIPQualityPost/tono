import numpy as np
from tests.node_tests._shared import make_field


def test_level_rotate_removes_tilt():
    from backend.nodes.level_rotate import LevelRotate

    node = LevelRotate()
    y, x = np.mgrid[:64, :64].astype(np.float64)
    data = 2.0 * x + 3.0 * y
    field = make_field(data=data)

    (result,) = node.process(field)
    assert result.data.shape == data.shape
    assert result.data.std() < data.std() * 0.25


def test_level_rotate_preserves_shape():
    from backend.nodes.level_rotate import LevelRotate

    node = LevelRotate()
    data = np.random.default_rng(42).standard_normal((48, 48))
    field = make_field(data=data)

    (result,) = node.process(field)
    assert result.data.shape == (48, 48)


def test_level_rotate_flat_noop():
    from backend.nodes.level_rotate import LevelRotate

    node = LevelRotate()
    data = np.ones((32, 32)) * 7.0
    field = make_field(data=data)

    (result,) = node.process(field)
    assert np.allclose(result.data, 7.0, atol=1e-6)
