import numpy as np
import pytest


def _make_mask():
    """Create a simple test mask: 10x10 block of 255 in a 64x64 field."""
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    return mask


def test_output_shape():
    from backend.nodes.mask_shift import MaskShift
    node = MaskShift()
    mask = _make_mask()

    result, = node.process(mask, shift_x=5, shift_y=3, border_mode="zero")
    assert result.shape == mask.shape
    assert result.dtype == np.uint8

    result_wrap, = node.process(mask, shift_x=-10, shift_y=7, border_mode="wrap")
    assert result_wrap.shape == mask.shape

    result_mirror, = node.process(mask, shift_x=2, shift_y=-4, border_mode="mirror")
    assert result_mirror.shape == mask.shape


def test_zero_shift_unchanged():
    from backend.nodes.mask_shift import MaskShift
    node = MaskShift()
    mask = _make_mask()

    result_zero, = node.process(mask, shift_x=0, shift_y=0, border_mode="zero")
    assert np.array_equal(result_zero, mask)

    result_wrap, = node.process(mask, shift_x=0, shift_y=0, border_mode="wrap")
    assert np.array_equal(result_wrap, mask)

    result_mirror, = node.process(mask, shift_x=0, shift_y=0, border_mode="mirror")
    assert np.array_equal(result_mirror, mask)


def test_wrap_mode():
    from backend.nodes.mask_shift import MaskShift
    node = MaskShift()
    mask = _make_mask()

    # Shift block right by 60 pixels — the block at cols 10:20 should wrap
    # and appear at cols 70%64=6 to 80%64=16, spanning the boundary.
    result, = node.process(mask, shift_x=60, shift_y=0, border_mode="wrap")
    assert result.dtype == np.uint8
    # The total number of masked pixels should be preserved in wrap mode
    assert np.count_nonzero(result) == np.count_nonzero(mask)
    # Original location should not all still be set
    # (shift is large enough to move block away from original position)
    assert not np.array_equal(result, mask)


def test_zero_mode_fills():
    from backend.nodes.mask_shift import MaskShift
    node = MaskShift()
    mask = _make_mask()

    # Shift right by 5 — left 5 columns should be zeroed
    result, = node.process(mask, shift_x=5, shift_y=0, border_mode="zero")
    assert np.all(result[:, :5] == 0)
    # Block should now be at cols 15:25, rows 10:20
    assert np.all(result[10:20, 15:25] == 255)

    # Shift down by 5 — top 5 rows should be zeroed
    result2, = node.process(mask, shift_x=0, shift_y=5, border_mode="zero")
    assert np.all(result2[:5, :] == 0)
    # Block should now be at rows 15:25, cols 10:20
    assert np.all(result2[15:25, 10:20] == 255)
