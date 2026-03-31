import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _make_mask(shape, defect_positions):
    """Create a uint8 mask array with 255 at given (row, col) positions."""
    mask = np.zeros(shape, dtype=np.uint8)
    for r, c in defect_positions:
        mask[r, c] = 255
    return mask


def test_spot_removal_no_mask_returns_field_unchanged():
    """Without a mask input the field should be returned as-is."""
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    field = make_field()
    result, = node.process(field, method="laplace", max_iter=50)
    # Should be the identical object (short-circuit path)
    assert result is field


def test_spot_removal_zero_fill():
    """method='zero' sets defect pixels to exactly 0."""
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    data = np.ones((16, 16)) * 5.0
    field = make_field(data=data)
    mask = _make_mask((16, 16), [(4, 4), (8, 8)])
    result, = node.process(field, method="zero", max_iter=1, mask=mask)
    assert result.data[4, 4] == pytest.approx(0.0)
    assert result.data[8, 8] == pytest.approx(0.0)
    # Non-defect pixels should stay 5.0
    assert result.data[0, 0] == pytest.approx(5.0)


def test_spot_removal_mean_fill_surrounded_by_constant():
    """On a constant field, mean fill should give back the constant."""
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    data = np.full((16, 16), 3.0)
    field = make_field(data=data)
    mask = _make_mask((16, 16), [(7, 7)])
    result, = node.process(field, method="mean", max_iter=1, mask=mask)
    assert result.data[7, 7] == pytest.approx(3.0, abs=1e-10)


def test_spot_removal_laplace_fill_surrounded_by_constant():
    """Laplace fill on a constant field should recover the constant at the defect."""
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    data = np.full((16, 16), 2.5)
    field = make_field(data=data)
    mask = _make_mask((16, 16), [(8, 8)])
    result, = node.process(field, method="laplace", max_iter=200, mask=mask)
    assert result.data[8, 8] == pytest.approx(2.5, abs=1e-3)


def test_spot_removal_laplace_smooth_interpolation():
    """Laplace should interpolate between boundary values smoothly."""
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    # Left half = 0, right half = 10; single defect in the middle
    data = np.zeros((16, 16))
    data[:, 8:] = 10.0
    field = make_field(data=data)
    # Defect at the boundary column
    mask = _make_mask((16, 16), [(8, 7)])
    result, = node.process(field, method="laplace", max_iter=500, mask=mask)
    # The filled value should be between 0 and 10
    filled = result.data[8, 7]
    assert 0.0 <= filled <= 10.0


def test_spot_removal_shape_preserved():
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    field = make_field(shape=(48, 64))
    mask = _make_mask((48, 64), [(10, 20)])
    result, = node.process(field, method="mean", max_iter=10, mask=mask)
    assert result.data.shape == (48, 64)


def test_spot_removal_mask_shape_mismatch_raises():
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    field = make_field(shape=(16, 16))
    bad_mask = np.ones((32, 32), dtype=np.uint8)
    with pytest.raises(ValueError, match="Mask shape"):
        node.process(field, method="zero", max_iter=1, mask=bad_mask)


def test_spot_removal_empty_mask_unchanged():
    """An all-zero mask means no defects — field returned unchanged."""
    from backend.nodes.spot_removal import SpotRemoval

    node = SpotRemoval()
    data = np.random.default_rng(0).standard_normal((16, 16))
    field = make_field(data=data)
    mask = np.zeros((16, 16), dtype=np.uint8)
    result, = node.process(field, method="laplace", max_iter=50, mask=mask)
    assert result is field
