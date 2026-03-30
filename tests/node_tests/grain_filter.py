import numpy as np
import pytest


def _make_mask(*rects):
    """Create a 30x30 uint8 mask with 255 in the given (row_start, row_end, col_start, col_end) rects."""
    m = np.zeros((30, 30), dtype=np.uint8)
    for r0, r1, c0, c1 in rects:
        m[r0:r1, c0:c1] = 255
    return m


def test_grain_filter_min_area():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    # Small grain: 2×2 = 4 px; large grain: 6×6 = 36 px
    mask = _make_mask((1, 3, 1, 3), (15, 21, 15, 21))

    # Remove grains smaller than 10 px → only large grain survives
    result, = node.process(mask, min_area=10, max_area=0, remove_border=False)
    assert result[1:3, 1:3].sum() == 0      # small grain removed
    assert result[15:21, 15:21].sum() > 0   # large grain kept


def test_grain_filter_max_area():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    mask = _make_mask((1, 3, 1, 3), (15, 21, 15, 21))

    # Remove grains larger than 10 px → only small grain survives
    result, = node.process(mask, min_area=1, max_area=10, remove_border=False)
    assert result[1:3, 1:3].sum() > 0       # small grain kept
    assert result[15:21, 15:21].sum() == 0  # large grain removed


def test_grain_filter_remove_border():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    # Border grain (touches top-left corner) and interior grain
    mask = _make_mask((0, 3, 0, 3), (10, 15, 10, 15))

    result, = node.process(mask, min_area=1, max_area=0, remove_border=True)
    assert result[0:3, 0:3].sum() == 0      # border grain removed
    assert result[10:15, 10:15].sum() > 0   # interior grain kept


def test_grain_filter_no_grains():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    mask = np.zeros((20, 20), dtype=np.uint8)

    result, = node.process(mask, min_area=1, max_area=0, remove_border=False)
    assert result.sum() == 0


def test_grain_filter_all_grains_kept():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    mask = _make_mask((5, 9, 5, 9), (15, 19, 15, 19))

    # Permissive thresholds: no grains should be removed
    result, = node.process(mask, min_area=1, max_area=0, remove_border=False)
    assert result[5:9, 5:9].sum() > 0
    assert result[15:19, 15:19].sum() > 0


def test_grain_filter_max_area_zero_means_no_limit():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    # Large grain 10×10 = 100 px; max_area=0 means no upper limit
    mask = _make_mask((5, 15, 5, 15))

    result, = node.process(mask, min_area=1, max_area=0, remove_border=False)
    assert result[5:15, 5:15].sum() > 0


def test_grain_filter_output_dtype():
    from backend.nodes.grain_filter import GrainFilter

    node = GrainFilter()
    mask = _make_mask((5, 10, 5, 10))

    result, = node.process(mask, min_area=1, max_area=0, remove_border=False)
    assert result.dtype == np.uint8
    assert set(result.flat).issubset({0, 255})
