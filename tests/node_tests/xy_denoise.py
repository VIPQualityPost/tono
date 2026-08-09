import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _reference_xy(x, y, do_average):
    """Direct numpy implementation: forward FFT of both scans, shared modulus
    = min of the two amplitudes, phase from x (or averaged), backward transform."""
    tiny = np.finfo(np.float64).tiny
    fx = np.fft.fft2(x)
    fy = np.fft.fft2(y)
    xm = np.abs(fx)
    ym = np.abs(fy)
    cosx = fx.real / np.maximum(xm, tiny)
    sinx = fx.imag / np.maximum(xm, tiny)
    if do_average:
        cosx = 0.5 * (cosx + fy.real / np.maximum(ym, tiny))
        sinx = 0.5 * (sinx + fy.imag / np.maximum(ym, tiny))
    return np.fft.ifft2(np.minimum(xm, ym) * (cosx + 1j * sinx)).real


def test_xy_denoise_output_arity():
    from backend.nodes.xy_denoise import XYDenoise

    rng = np.random.default_rng(0)
    field = make_field(data=rng.standard_normal((32, 32)))
    node = XYDenoise()
    result = node.process(field, field, do_average=True)
    assert len(result) == len(node.OUTPUTS) == 1


def test_xy_denoise_identical_scans_reconstruct():
    """Two identical scans reproduce the input exactly."""
    from backend.nodes.xy_denoise import XYDenoise

    rng = np.random.default_rng(1)
    data = rng.standard_normal((24, 28))
    field = make_field(data=data)
    node = XYDenoise()
    (out,) = node.process(field, field, do_average=False)
    assert np.allclose(out.data, data, rtol=1e-10, atol=1e-12)
    (out_avg,) = node.process(field, field, do_average=True)
    assert np.allclose(out_avg.data, data, rtol=1e-10, atol=1e-12)


def test_xy_denoise_matches_reference():
    """Node output equals the per-frequency min-modulus phase-average algorithm
    from xydenoise.c for a range of inputs."""
    from backend.nodes.xy_denoise import XYDenoise

    rng = np.random.default_rng(2)
    node = XYDenoise()
    for do_average in (False, True):
        for _ in range(3):
            x = rng.standard_normal((16, 16))
            y = rng.standard_normal((16, 16))
            (out,) = node.process(make_field(data=x), make_field(data=y), do_average=do_average)
            assert np.allclose(out.data, _reference_xy(x, y, do_average), rtol=1e-10, atol=1e-12)


def test_xy_denoise_removes_dc_offset_from_one_scan():
    """x = common + constant offset, y = common: the shared (min) modulus keeps
    only the common component, so the DC offset of the x scan is removed and the
    result reproduces the common field."""
    from backend.nodes.xy_denoise import XYDenoise

    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:32, 0:32]
    common = 5.0 * np.exp(-((xx - 16) ** 2 + (yy - 16) ** 2) / 64.0)
    common = common - common.mean()  # zero-mean common component
    x = common + 50.0
    y = common
    node = XYDenoise()
    (out,) = node.process(make_field(data=x), make_field(data=y), do_average=False)
    assert np.allclose(out.data, common, rtol=1e-10, atol=1e-10)
    (out_avg,) = node.process(make_field(data=x), make_field(data=y), do_average=True)
    assert np.allclose(out_avg.data, common, rtol=1e-10, atol=1e-10)


def test_xy_denoise_suppresses_directional_artefacts():
    """A vertical stripe present only in the x scan and a horizontal stripe only
    in the y scan are suppressed: the result is closer to the common field than
    either input."""
    from backend.nodes.xy_denoise import XYDenoise

    rng = np.random.default_rng(4)
    yy, xx = np.mgrid[0:64, 0:64]
    common = 8.0 * np.exp(-((xx - 32) ** 2 + (yy - 32) ** 2) / 200.0)
    x = common.copy()
    x[:, 8] += 30.0  # vertical stripe in the x scan
    x[:, 40] += 30.0
    y = common.copy()
    y[8, :] += 30.0  # horizontal stripe in the y scan
    y[40, :] += 30.0

    node = XYDenoise()
    (out,) = node.process(make_field(data=x), make_field(data=y), do_average=True)
    rmse_out = float(np.sqrt(np.mean((out.data - common) ** 2)))
    rmse_x = float(np.sqrt(np.mean((x - common) ** 2)))
    rmse_y = float(np.sqrt(np.mean((y - common) ** 2)))
    assert rmse_out < 0.5 * min(rmse_x, rmse_y)


def test_xy_denoise_preserves_metadata():
    from backend.nodes.xy_denoise import XYDenoise

    rng = np.random.default_rng(5)
    field_x = make_field(data=rng.standard_normal((16, 16)), xreal=2e-6, yreal=3e-6)
    field_y = make_field(data=rng.standard_normal((16, 16)), xreal=2e-6, yreal=3e-6)
    field_y.si_unit_z = "V"
    field_x.si_unit_z = "V"
    node = XYDenoise()
    (out,) = node.process(field_x, field_y, do_average=True)
    assert out.data.shape == field_x.data.shape
    assert out.xreal == 2e-6 and out.yreal == 3e-6
    assert out.si_unit_xy == "m" and out.si_unit_z == "V"
    assert out.xoff == field_x.xoff and out.yoff == field_x.yoff


def test_xy_denoise_errors():
    from backend.nodes.xy_denoise import XYDenoise

    node = XYDenoise()
    field = make_field()
    other_shape = make_field(data=np.ones((16, 16)))
    with pytest.raises(ValueError):
        node.process(field, other_shape, do_average=True)
    # unit mismatch
    other_unit = make_field()
    other_unit.si_unit_z = "V"
    with pytest.raises(ValueError):
        node.process(field, other_unit, do_average=True)
    # extent mismatch
    other_extent = make_field(xreal=2e-6)
    with pytest.raises(ValueError):
        node.process(field, other_extent, do_average=True)
