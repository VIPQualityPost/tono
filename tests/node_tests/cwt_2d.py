import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _sinusoid(cycles=4, size=64, amplitude=2.0):
    """2-D sinusoid along x: pure frequency at |k| = cycles with the 2π·cycles
    phase gradient over the row, broadcast to a (size, size) field."""
    j = np.arange(size)[np.newaxis, :]
    return amplitude * np.sin(2.0 * np.pi * cycles * j / size)


def test_cwt_2d_output_arity():
    from backend.nodes.cwt_2d import CWT2D

    node = CWT2D()
    field = make_field(data=np.random.default_rng(3).standard_normal((32, 32)))
    result = node.process(field, wavelet="gaussian", min_scale_px=2.0, max_scale_px=8.0, n_scales=4)
    assert len(result) == len(node.OUTPUTS) == 1


def test_cwt_gaussian_single_scale_value():
    """Single-scale Gaussian CWT of a sinusoid is the sinusoid scaled by the
    wavelet w = exp(-(s^2*cur^2)/2), cur = 4*k/xres — the gwy_cwt_wfunc_2d formula."""
    from backend.nodes.cwt_2d import _cwt_scale_response

    data = _sinusoid(cycles=4, size=64)  # wavelength 16 px -> cur = 4*4/64 = 0.25
    resp = _cwt_scale_response(data, 2.0, "gaussian")
    expected = 2.0 * np.exp(-0.5 * (2.0 * 0.25) ** 2)  # scale2*cur2 = 0.25
    assert np.isclose(np.abs(resp).max(), expected, rtol=1e-9)
    # response oscillates with the signal wavelength
    assert resp.shape == data.shape


def test_cwt_mexican_hat_peaks_at_half_wavelength():
    """Hat wavelet w = (s^2 cur^2) exp(-(s^2 cur^2)/2) 2 pi s^2 peaks at s = 2/cur
    = wavelength/2 (= 8 px for the 16 px sinusoid)."""
    from backend.nodes.cwt_2d import _cwt_scale_response

    data = _sinusoid(cycles=4, size=64)
    r_at_peak = _cwt_scale_response(data, 8.0, "mexican_hat")
    r_off = _cwt_scale_response(data, 2.0, "mexican_hat")
    r_large = _cwt_scale_response(data, 30.0, "mexican_hat")
    peak = np.abs(r_at_peak).max()
    assert peak > 20 * np.abs(r_off).max()
    assert peak > 50 * np.abs(r_large).max()
    # Exact value: A * 2*pi*s^2 * (s^2 cur^2) exp(-(s^2 cur^2)/2), s^2 cur^2 = 4
    expected = 2.0 * 2.0 * np.pi * 64.0 * 4.0 * np.exp(-2.0)
    assert np.isclose(peak, expected, rtol=1e-9)


def test_cwt_scale_ordering_gaussian():
    """A small scale keeps more of the fine sinusoid than a large scale."""
    from backend.nodes.cwt_2d import _cwt_scale_response

    data = _sinusoid(cycles=4, size=64)
    small = np.abs(_cwt_scale_response(data, 1.0, "gaussian")).max()
    large = np.abs(_cwt_scale_response(data, 40.0, "gaussian")).max()
    assert small > 100 * large


def test_cwt_constant_field():
    """Gaussian passes DC (response = |mean|); Mexican hat suppresses DC."""
    from backend.nodes.cwt_2d import CWT2D

    field = make_field(data=np.full((32, 32), 7.5))
    node = CWT2D()
    (gauss,) = node.process(field, wavelet="gaussian", min_scale_px=2.0, max_scale_px=8.0, n_scales=3)
    assert np.allclose(gauss.data, 7.5)
    (hat,) = node.process(field, wavelet="mexican_hat", min_scale_px=2.0, max_scale_px=8.0, n_scales=3)
    assert np.abs(hat.data).max() < 1e-9


def test_cwt_sweep_maximum():
    """Node output is the max over scales of the absolute single-scale response."""
    from backend.nodes.cwt_2d import CWT2D, _cwt_scale_response

    field = make_field(data=_sinusoid(cycles=4, size=64))
    node = CWT2D()
    (out,) = node.process(field, wavelet="mexican_hat", min_scale_px=7.0, max_scale_px=9.0, n_scales=3)
    scales = np.linspace(7.0, 9.0, 3)
    expected = np.maximum.reduce([np.abs(_cwt_scale_response(field.data, s, "mexican_hat")) for s in scales])
    assert np.array_equal(out.data, expected)
    # sweep far from the matching scale is much weaker
    (weak,) = node.process(field, wavelet="mexican_hat", min_scale_px=1.0, max_scale_px=2.0, n_scales=2)
    assert out.data.max() > 20 * weak.data.max()


def test_cwt_preserves_metadata():
    from backend.nodes.cwt_2d import CWT2D

    field = make_field(data=_sinusoid(cycles=4, size=64))
    node = CWT2D()
    (out,) = node.process(field, wavelet="gaussian", min_scale_px=1.0, max_scale_px=4.0, n_scales=3)
    assert out.data.shape == field.data.shape
    assert out.xreal == field.xreal and out.yreal == field.yreal
    assert out.si_unit_xy == field.si_unit_xy and out.si_unit_z == field.si_unit_z
    assert out.xoff == field.xoff and out.yoff == field.yoff


@pytest.mark.parametrize("kwargs", [
    {"n_scales": 0},
    {"n_scales": -3},
    {"min_scale_px": 10.0, "max_scale_px": 5.0},
    {"min_scale_px": 0.0},
    {"wavelet": "morlet"},
])
def test_cwt_errors(kwargs):
    from backend.nodes.cwt_2d import CWT2D

    field = make_field()
    node = CWT2D()
    args = {"wavelet": "gaussian", "min_scale_px": 1.0, "max_scale_px": 5.0, "n_scales": 3}
    args.update(kwargs)
    with pytest.raises(ValueError):
        node.process(field, **args)
