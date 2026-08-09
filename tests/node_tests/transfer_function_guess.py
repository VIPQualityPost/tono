"""Tests for the Transfer Function Guess node."""

import numpy as np
import pytest

from backend.data_types import DataField


def _make_tf_scenario(shape=(64, 64), sigma_px=2.0, seed=5):
    """Periodic full-spectrum ideal convolved with a Gaussian PSF (peak at origin)."""
    yres, xres = shape
    rng = np.random.default_rng(seed)
    ideal = rng.standard_normal(shape) + 2.0
    yy, xx = np.mgrid[0:yres, 0:xres]
    psf_origin = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma_px ** 2))
    meas = np.real(np.fft.ifft2(np.fft.fft2(ideal - ideal.mean()) * np.fft.fft2(psf_origin)))
    meas = meas + ideal.mean()
    dx = 1e-7
    field = DataField(data=meas, xreal=xres * dx, yreal=yres * dx, si_unit_xy="m", si_unit_z="m")
    ideal_field = DataField(data=ideal, xreal=xres * dx, yreal=yres * dx, si_unit_xy="m", si_unit_z="m")
    return field, ideal_field, psf_origin, dx


def test_outputs_arity():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    assert len(TransferFunctionGuess.OUTPUTS) == 2
    field, ideal_f, _, _ = _make_tf_scenario()
    out = TransferFunctionGuess().process(field, ideal_f, method="regularised", sigma_log10=0.0,
                                          auto_sigma=False, txres=33, tyres=33, border=3,
                                          windowing="none", as_integral=True)
    assert isinstance(out, tuple) and len(out) == 2


def test_regularised_recovers_gaussian_psf():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    field, ideal_f, psf_origin, dx = _make_tf_scenario(shape=(64, 64))
    psf, table = TransferFunctionGuess().process(field, ideal_f, method="regularised", sigma_log10=0.0,
                                                 auto_sigma=False, txres=33, tyres=33, border=3,
                                                 windowing="none", as_integral=True)
    # TF is cropped to 33x33 centered on the image center.
    assert psf.data.shape == (33, 33)
    assert np.unravel_index(np.argmax(psf.data), psf.data.shape) == (16, 16)
    # Slight blurring by the regularisation keeps the profile very close.
    prof = psf.data[16, :] / psf.data[16, :].sum()
    gt = np.fft.fftshift(psf_origin)[32, 16:49]
    gt = gt / gt.sum()
    assert np.corrcoef(prof, gt)[0, 1] > 0.85
    # Metadata: lateral units and geometry follow the measured field; the crop
    # keeps the physical position of the PSF (border = (xres-txres+1)/2).
    assert psf.si_unit_xy == "m"
    assert np.isclose(psf.xreal, 33 * dx)
    assert np.isclose(psf.xoff, (64 - 33 + 1) // 2 * dx)
    # Transfer function value unit: z_meas/z_ideal * xy^-2 = m^-2.
    assert psf.si_unit_z == "m^-2"
    # Measurement table rows.
    assert len(table) == 5
    for row in table:
        assert set(row) == {"quantity", "value", "unit"}
    quantities = [row["quantity"] for row in table]
    assert quantities == ["TF width", "TF height", "TF norm", "Difference norm", "Regularization sigma"]
    assert table[0]["unit"] == "m"
    assert table[0]["value"] > 0.0
    assert np.isclose(table[4]["value"], 10.0 ** 0.0)


def test_wiener_recovers_gaussian_psf():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    field, ideal_f, psf_origin, _ = _make_tf_scenario(shape=(64, 64))
    psf, table = TransferFunctionGuess().process(field, ideal_f, method="wiener", sigma_log10=-2.0,
                                                 auto_sigma=False, txres=33, tyres=33, border=3,
                                                 windowing="none", as_integral=True)
    assert np.unravel_index(np.argmax(psf.data), psf.data.shape) == (16, 16)
    prof = psf.data[16, :] / psf.data[16, :].sum()
    gt = np.fft.fftshift(psf_origin)[32, 16:49]
    gt = gt / gt.sum()
    assert np.corrcoef(prof, gt)[0, 1] > 0.9


def test_least_squares_recovers_gaussian_psf():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    field, ideal_f, psf_origin, dx = _make_tf_scenario(shape=(48, 48), seed=11)
    psf, table = TransferFunctionGuess().process(field, ideal_f, method="least_squares", sigma_log10=-4.0,
                                                 auto_sigma=False, txres=17, tyres=17, border=3,
                                                 windowing="none", as_integral=True)
    assert psf.data.shape == (17, 17)
    assert np.unravel_index(np.argmax(psf.data), psf.data.shape) == (8, 8)
    prof = psf.data[8, :] / psf.data[8, :].sum()
    gt = np.fft.fftshift(psf_origin)[24, 16:33]
    gt = gt / gt.sum()
    assert np.corrcoef(prof, gt)[0, 1] > 0.85
    # Least-squares TF is centered on its own window (xoff = -0.5*want_txres*dx).
    assert np.isclose(psf.xreal, 17 * dx)
    assert np.isclose(psf.xoff, -0.5 * 17 * dx)
    assert psf.data.dtype == np.float64


def test_integral_vs_discrete_normalisation():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    field, ideal_f, _, dx = _make_tf_scenario(shape=(64, 64))
    node = TransferFunctionGuess()
    psf_i, table_i = node.process(field, ideal_f, method="regularised", sigma_log10=0.0,
                                  auto_sigma=False, txres=33, tyres=33, border=3,
                                  windowing="none", as_integral=True)
    psf_d, table_d = node.process(field, ideal_f, method="regularised", sigma_log10=0.0,
                                  auto_sigma=False, txres=33, tyres=33, border=3,
                                  windowing="none", as_integral=False)
    # Non-integral normalisation scales the PSF by dx*dy and notes it in the unit
    # (m^-2 * m^2 collapses to a dimensionless quantity).
    assert np.allclose(psf_d.data, psf_i.data * dx * dx)
    assert psf_d.si_unit_z == ""
    # The TF width row scales with the values.
    width_i = [r for r in table_i if r["quantity"] == "TF width"][0]["value"]
    width_d = [r for r in table_d if r["quantity"] == "TF width"][0]["value"]
    assert np.isclose(width_d, width_i * dx * dx, rtol=1e-9)


def test_auto_sigma_runs():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    field, ideal_f, _, _ = _make_tf_scenario(shape=(64, 64))
    psf, table = TransferFunctionGuess().process(field, ideal_f, method="regularised", sigma_log10=1.0,
                                                 auto_sigma=True, txres=33, tyres=33, border=3,
                                                 windowing="welch", as_integral=True)
    sigma = [row for row in table if row["quantity"] == "Regularization sigma"][0]["value"]
    assert sigma > 0.0
    assert psf.data.shape == (33, 33)


def test_error_on_mismatched_ideal():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    field, ideal_f, _, _ = _make_tf_scenario(shape=(64, 64))
    small = DataField(data=ideal_f.data[:32, :32], xreal=32e-7, yreal=32e-7,
                      si_unit_xy="m", si_unit_z="m")
    with pytest.raises(ValueError, match="same resolution"):
        TransferFunctionGuess().process(field, small, method="regularised", sigma_log10=0.0,
                                        auto_sigma=False, txres=33, tyres=33, border=3,
                                        windowing="none", as_integral=True)


def test_error_on_too_small_field():
    from backend.nodes.transfer_function_guess import TransferFunctionGuess

    rng = np.random.default_rng(3)
    data = rng.standard_normal((16, 16))
    field = DataField(data=data, xreal=16e-7, yreal=16e-7, si_unit_xy="m", si_unit_z="m")
    ideal_f = DataField(data=data + 0.1, xreal=16e-7, yreal=16e-7, si_unit_xy="m", si_unit_z="m")
    with pytest.raises(ValueError, match="too small"):
        TransferFunctionGuess().process(field, ideal_f, method="regularised", sigma_log10=0.0,
                                        auto_sigma=False, txres=9, tyres=9, border=0,
                                        windowing="none", as_integral=True)
