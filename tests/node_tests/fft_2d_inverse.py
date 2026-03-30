import numpy as np
from backend.data_types import DataField
from tests.node_tests._shared import make_field


def _make_freq_field(N=32):
    """Return a frequency-domain DataField built from a real spatial field."""
    from backend.nodes.fft_2d import FFT2D
    field = make_field(data=np.random.default_rng(0).standard_normal((N, N)), xreal=1e-6, yreal=1e-6)
    spectrum, spec_mag, spec_phase, spec_psdf = FFT2D().process(field, windowing="none", level="none")
    return spectrum, spec_mag, spec_phase, spec_psdf, field


def test_fft2d_inverse_magnitude():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    spectrum, spec_mag, spec_phase, _, original = _make_freq_field()
    result, = node.process(spec_mag, representation="magnitude", phase=spec_phase)
    assert isinstance(result, DataField)
    assert result.domain == "spatial"
    assert result.data.shape == original.data.shape
    assert np.allclose(result.data, original.data, atol=1e-9)


def test_fft2d_inverse_log_magnitude():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    _, spec_mag, spec_phase, _, original = _make_freq_field()
    from backend.nodes.fft_2d import FFT2D
    field = make_field(data=np.random.default_rng(1).standard_normal((32, 32)), xreal=1e-6, yreal=1e-6)
    spectrum, spec_mag2, spec_phase2, _ = FFT2D().process(field, windowing="none", level="none")
    # log_magnitude = log1p(magnitude), so inverse should recover original
    result, = node.process(spec_mag2, representation="log_magnitude", phase=spec_phase2)
    assert result.domain == "spatial"
    assert result.data.shape == field.data.shape


def test_fft2d_inverse_psdf():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    _, _, _, spec_psdf, original = _make_freq_field()
    result, = node.process(spec_psdf, representation="psdf")
    assert result.domain == "spatial"
    assert result.data.shape == original.data.shape


def test_fft2d_inverse_no_phase():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    _, spec_mag, _, _, original = _make_freq_field()
    result, = node.process(spec_mag, representation="magnitude")
    assert result.domain == "spatial"
    assert result.data.shape == original.data.shape


def test_fft2d_inverse_spatial_domain_raises():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    spatial_field = make_field(data=np.ones((16, 16)))
    assert spatial_field.domain == "spatial"
    try:
        node.process(spatial_field, representation="magnitude")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_fft2d_inverse_unsupported_representation():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    _, spec_mag, _, _, _ = _make_freq_field()
    try:
        node.process(spec_mag, representation="invalid_repr")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_fft2d_inverse_phase_shape_mismatch():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    _, spec_mag, spec_phase, _, _ = _make_freq_field(N=32)
    _, spec_mag_big, spec_phase_big, _, _ = _make_freq_field(N=64)
    try:
        node.process(spec_mag, representation="magnitude", phase=spec_phase_big)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_fft2d_inverse_phase_not_frequency_domain():
    from backend.nodes.fft_2d_inverse import FFT2DInverse
    node = FFT2DInverse()
    _, spec_mag, _, _, _ = _make_freq_field()
    spatial_phase = make_field(data=np.zeros((32, 32)))
    try:
        node.process(spec_mag, representation="magnitude", phase=spatial_phase)
        assert False, "Expected ValueError"
    except ValueError:
        pass
