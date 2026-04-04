import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import bool_to_mask


def test_laplace_fills_hole():
    from backend.nodes.laplace_interpolation import LaplaceInterpolation

    node = LaplaceInterpolation()
    data = np.ones((32, 32)) * 5.0
    mask = np.zeros((32, 32), dtype=bool)
    mask[10:20, 10:20] = True
    data[mask] = 0.0  # hole
    field = make_field(data=data)
    result, = node.process(field, bool_to_mask(mask), 200)
    # Filled region should be close to surrounding value of 5.0
    assert result.data[15, 15] > 3.0


def test_laplace_no_mask_unchanged():
    from backend.nodes.laplace_interpolation import LaplaceInterpolation

    node = LaplaceInterpolation()
    field = make_field(shape=(32, 32))
    mask = bool_to_mask(np.zeros((32, 32), dtype=bool))
    result, = node.process(field, mask, 100)
    assert np.allclose(result.data, field.data)


def test_laplace_preserves_shape():
    from backend.nodes.laplace_interpolation import LaplaceInterpolation

    node = LaplaceInterpolation()
    field = make_field(shape=(48, 64))
    mask = np.zeros((48, 64), dtype=bool)
    mask[20:30, 20:40] = True
    result, = node.process(field, bool_to_mask(mask), 50)
    assert result.data.shape == (48, 64)
