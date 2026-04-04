import numpy as np
from scipy.ndimage import gaussian_filter
from tests.node_tests._shared import make_field


def _make_test_pair(shape=(64, 64), sigma=2.0):
    """Return (measured, ideal) where measured = gaussian_filter(ideal)."""
    ideal = make_field(shape=shape)
    measured_data = gaussian_filter(ideal.data, sigma=sigma)
    measured = make_field(data=measured_data)
    return measured, ideal


def test_output_shape():
    from backend.nodes.psf_estimation import PSFEstimation

    node = PSFEstimation()
    measured, ideal = _make_test_pair()
    psf_field, _ = node.process(measured, ideal, "wiener", 0.01, 32)
    assert psf_field.data.shape == (32, 32)


def test_psf_normalized():
    from backend.nodes.psf_estimation import PSFEstimation

    node = PSFEstimation()
    measured, ideal = _make_test_pair()
    for method in ("wiener", "least_squares", "gaussian_fit"):
        psf_field, _ = node.process(measured, ideal, method, 0.01, 32)
        assert abs(psf_field.data.sum() - 1.0) < 1e-6, (
            f"{method}: PSF sum = {psf_field.data.sum()}"
        )


def test_gaussian_fit_parameters():
    from backend.nodes.psf_estimation import PSFEstimation

    node = PSFEstimation()
    measured, ideal = _make_test_pair()
    _, parameters = node.process(measured, ideal, "gaussian_fit", 0.01, 32)
    names = {row["quantity"] for row in parameters}
    assert "sigma_x" in names
    assert "sigma_y" in names
    assert "amplitude" in names


def test_all_methods_finite():
    from backend.nodes.psf_estimation import PSFEstimation

    node = PSFEstimation()
    measured, ideal = _make_test_pair()
    for method in ("wiener", "least_squares", "gaussian_fit"):
        psf_field, _ = node.process(measured, ideal, method, 0.01, 32)
        assert np.isfinite(psf_field.data).all(), (
            f"{method}: PSF contains non-finite values"
        )
