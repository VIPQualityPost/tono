import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _make_node():
    from backend.nodes.rank_transform import RankTransform
    return RankTransform()


def _spike_field(size=9):
    """Field filled with 5.0 and a single 10.0 pixel at the centre."""
    data = np.full((size, size), 5.0)
    data[size // 2, size // 2] = 10.0
    return make_field(data=data)


def test_output_arity():
    node = _make_node()
    assert len(node.OUTPUTS) == 1
    assert node.OUTPUTS[0][0] == "DATA_FIELD"
    result = node.process(_spike_field(), size=1, filter_type="rank")
    assert isinstance(result, tuple) and len(result) == 1


def test_rank_transform_exact_3x3_values():
    """For a 3x3 window (size=1) the exact ranks are known: 8.5/9 at the spike,
    4/9 one pixel away, 1/2 far away; min-max normalization maps them to
    1, 0 and 1/9."""
    node = _make_node()
    (out,) = node.process(_spike_field(), size=1, filter_type="rank")
    assert out.data[4, 4] == pytest.approx(1.0)
    assert out.data[3, 3] == pytest.approx(0.0)
    assert out.data[4, 3] == pytest.approx(0.0)
    assert out.data[0, 0] == pytest.approx(1.0 / 9.0)
    assert out.data.min() >= 0.0 and out.data.max() <= 1.0


def test_rank_ramp_exact_values():
    """A 3x3 ramp 0..8 with size=1: windows are truncated at the borders, so
    the normalized ranks are exactly (hand-computed from the C formula)."""
    node = _make_node()
    data = np.arange(9, dtype=np.float64).reshape(3, 3)
    (out,) = node.process(make_field(data=data), size=1, filter_type="rank")
    expected = np.array([
        [0.0, 1 / 6, 1 / 3],
        [7 / 18, 0.5, 11 / 18],
        [2 / 3, 5 / 6, 1.0],
    ])
    assert np.allclose(out.data, expected, atol=1e-12)
    # Normalized ranks are strictly increasing in the value
    assert np.all(np.diff(out.data, axis=1) > 0)
    assert np.all(np.diff(out.data, axis=0) > 0)


def _reference_local_rank(data, asize):
    """Direct per-pixel reference implementation used as the expected
    value (clamped elliptical window, ties weighted 1/2)."""
    yres, xres = data.shape
    size = 2 * asize + 1
    out = np.empty_like(data)
    for row in range(yres):
        yfrom, yto = max(0, row - asize), min(yres - 1, row + asize)
        for col in range(xres):
            v = data[row, col]
            r = hr = t = 0
            for i in range(yfrom, yto + 1):
                k = i - row
                xr = int(np.floor(np.sqrt(0.25 * size * size - k * k)))
                xfrom, xto = max(0, col - xr), min(xres - 1, col + xr)
                for j in range(xfrom, xto + 1):
                    d = data[i, j]
                    if d <= v:
                        r += 1
                        if d == v:
                            hr += 1
                    t += 1
            out[row, col] = (r - 0.5 * hr) / t
    return out


def test_rank_matches_c_reference():
    """The chunked implementation reproduces the C local_rank() exactly on a
    random field (including the truncated border windows)."""
    node = _make_node()
    rng = np.random.default_rng(7)
    data = rng.integers(0, 4, (9, 11)).astype(np.float64)  # ties make hr matter
    for size in (1, 2, 3):
        (out,) = node.process(make_field(data=data), size=size, filter_type="rank")
        expected = _reference_local_rank(data, size)
        dmin, dmax = expected.min(), expected.max()
        if dmax > dmin:
            expected = (expected - dmin) / (dmax - dmin)
        else:
            expected = np.zeros_like(expected)
        assert np.allclose(out.data, expected, atol=1e-12), size


def test_taller_spike_outranks_shorter_in_shared_window():
    """Within one window the taller feature has a strictly higher rank."""
    node = _make_node()
    data = np.full((9, 9), 1.0)
    data[4, 3] = 2.0
    data[4, 4] = 3.0
    (out,) = node.process(make_field(data=data), size=1, filter_type="rank")
    # Exact ranks: 8.5/9 for the 3.0 pixel, 7.5/9 for the 2.0 pixel, 3.5/9
    # for pixels whose window contains both spikes, 4.5/9 for all-1 windows
    assert out.data[4, 4] == pytest.approx(1.0)
    assert out.data[4, 3] == pytest.approx((7.5 - 3.5) / (8.5 - 3.5))
    assert out.data[0, 0] == pytest.approx((4.5 - 3.5) / 5.0)
    assert out.data[3, 3] == pytest.approx(0.0)   # window with both spikes


def test_range_type_two_levels():
    """Range filter of a single spike: windows containing it have range 5,
    windows without it range 0; after normalization the output is 0/1."""
    node = _make_node()
    (out,) = node.process(_spike_field(), size=1, filter_type="range")
    assert set(np.unique(out.data)) <= {0.0, 1.0}
    assert out.data[4, 4] == pytest.approx(1.0)
    assert out.data[0, 0] == pytest.approx(0.0)


def test_normalization_type():
    """Local normalization: 1 at the spike centre, 0 in windows containing it
    (v == min), 0.5 for constant windows (the C convention), then normalized."""
    node = _make_node()
    (out,) = node.process(_spike_field(), size=1, filter_type="normalization")
    assert out.data[4, 4] == pytest.approx(1.0)
    assert out.data[3, 3] == pytest.approx(0.0)
    assert out.data[0, 0] == pytest.approx(0.5)


def test_constant_field_outputs_zeros():
    node = _make_node()
    (out,) = node.process(make_field(data=np.ones((8, 8))), size=2,
                          filter_type="rank")
    assert np.all(out.data == 0.0)
    (out2,) = node.process(make_field(data=np.ones((8, 8))), size=2,
                           filter_type="range")
    assert np.all(out2.data == 0.0)


def test_output_unitless_and_metadata():
    node = _make_node()
    field = _spike_field()
    (out,) = node.process(field, size=1, filter_type="rank")
    assert out.si_unit_z == ""
    assert out.si_unit_xy == field.si_unit_xy
    assert out.data.shape == field.data.shape
    assert out.xreal == field.xreal and out.yreal == field.yreal


def test_bigger_kernel_smoother_rank_field():
    """Larger kernels average over more pixels: the rank field has lower
    variance for a fixed noisy input."""
    node = _make_node()
    rng = np.random.default_rng(0)
    data = rng.standard_normal((32, 32))
    field = make_field(data=data)
    (out_small,) = node.process(field, size=2, filter_type="rank")
    (out_large,) = node.process(field, size=5, filter_type="rank")
    assert out_small.data.std() > out_large.data.std()


def test_invalid_filter_type_raises():
    node = _make_node()
    with pytest.raises(ValueError):
        node.process(_spike_field(), size=3, filter_type="bogus")


def test_invalid_size_raises():
    node = _make_node()
    with pytest.raises(ValueError):
        node.process(_spike_field(), size=0, filter_type="rank")
