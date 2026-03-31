import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_wavelet_denoise_shape_preserved():
    from backend.nodes.wavelet_denoise import WaveletDenoise

    node = WaveletDenoise()
    field = make_field(shape=(64, 64))
    result, = node.process(field, wavelet="db4", method="BayesShrink", sigma=0.0, mode="soft")
    assert result.data.shape == (64, 64)


def test_wavelet_denoise_reduces_noise():
    """Denoising noisy data should reduce standard deviation."""
    from backend.nodes.wavelet_denoise import WaveletDenoise

    rng = np.random.default_rng(0)
    clean = np.outer(np.linspace(0, 1, 32), np.linspace(0, 1, 32))
    noisy = clean + rng.normal(0, 0.1, clean.shape)
    field = make_field(data=noisy)
    node = WaveletDenoise()
    result, = node.process(field, wavelet="db4", method="BayesShrink", sigma=0.0, mode="soft")
    # Denoised should be closer to clean than the noisy input
    denoised_err = np.std(result.data - clean)
    noisy_err = np.std(noisy - clean)
    assert denoised_err < noisy_err


def test_wavelet_denoise_uniform_field_unchanged():
    """A flat field (no variation) is returned as-is."""
    from backend.nodes.wavelet_denoise import WaveletDenoise

    node = WaveletDenoise()
    field = make_field(data=np.full((32, 32), 5.0))
    result, = node.process(field, wavelet="db1", method="VisuShrink", sigma=0.0, mode="hard")
    # The short-circuit path returns the original field object
    assert result is field


def test_wavelet_denoise_preserves_range():
    """Output values should stay within the input data range (approx)."""
    from backend.nodes.wavelet_denoise import WaveletDenoise

    rng = np.random.default_rng(1)
    data = rng.standard_normal((32, 32))
    field = make_field(data=data)
    node = WaveletDenoise()
    result, = node.process(field, wavelet="db4", method="BayesShrink", sigma=0.0, mode="soft")
    # The normalisation ensures output is within [data.min(), data.max()]
    assert result.data.min() >= data.min() - 1e-10
    assert result.data.max() <= data.max() + 1e-10


def test_wavelet_denoise_all_wavelets():
    """All supported wavelets should run without error."""
    from backend.nodes.wavelet_denoise import WaveletDenoise

    rng = np.random.default_rng(2)
    field = make_field(data=rng.standard_normal((32, 32)))
    node = WaveletDenoise()
    for wavelet in ("db1", "db2", "db4", "db8", "sym4", "coif1", "bior1.3"):
        result, = node.process(field, wavelet=wavelet, method="BayesShrink", sigma=0.0, mode="soft")
        assert result.data.shape == field.data.shape


def test_wavelet_denoise_visu_shrink():
    from backend.nodes.wavelet_denoise import WaveletDenoise

    rng = np.random.default_rng(3)
    field = make_field(data=rng.standard_normal((32, 32)))
    node = WaveletDenoise()
    result, = node.process(field, wavelet="db4", method="VisuShrink", sigma=0.0, mode="soft")
    assert result.data.shape == field.data.shape


def test_wavelet_denoise_preserves_metadata():
    from backend.nodes.wavelet_denoise import WaveletDenoise

    node = WaveletDenoise()
    field = make_field()
    result, = node.process(field, wavelet="db4", method="BayesShrink", sigma=0.0, mode="soft")
    assert result.xreal == field.xreal
    assert result.si_unit_z == field.si_unit_z
