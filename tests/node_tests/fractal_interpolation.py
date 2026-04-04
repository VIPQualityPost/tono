import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import bool_to_mask


def test_fractal_fills_hole():
    from backend.nodes.fractal_interpolation import FractalInterpolation

    node = FractalInterpolation()
    data = np.random.default_rng(42).standard_normal((32, 32))
    mask = np.zeros((32, 32), dtype=bool)
    mask[12:20, 12:20] = True
    field = make_field(data=data)
    result, = node.process(field, bool_to_mask(mask), 50)
    assert result.data.shape == (32, 32)
    assert np.isfinite(result.data).all()


def test_fractal_no_mask_unchanged():
    from backend.nodes.fractal_interpolation import FractalInterpolation

    node = FractalInterpolation()
    field = make_field(shape=(32, 32))
    mask = bool_to_mask(np.zeros((32, 32), dtype=bool))
    result, = node.process(field, mask, 50)
    assert np.allclose(result.data, field.data)


def test_fractal_preserves_statistics():
    from backend.nodes.fractal_interpolation import FractalInterpolation

    node = FractalInterpolation()
    rng = np.random.default_rng(0)
    data = rng.standard_normal((64, 64))
    mask = np.zeros((64, 64), dtype=bool)
    mask[20:40, 20:40] = True
    field = make_field(data=data)
    result, = node.process(field, bool_to_mask(mask), 100)
    # Filled region should have similar statistics to the rest
    filled_std = result.data[mask].std()
    valid_std = data[~mask].std()
    assert filled_std > 0.1 * valid_std  # not flat
