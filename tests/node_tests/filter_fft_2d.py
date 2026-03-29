import numpy as np
from tests.node_tests._shared import make_field


def test_fft_filter_2d():
    from backend.nodes.filter_fft_2d import FFTFilter2D
    node = FFTFilter2D()

    N = 128
    y, x = np.mgrid[0:N, 0:N] / N
    low_2d = np.sin(2 * np.pi * 3 * x) + np.sin(2 * np.pi * 3 * y)
    high_2d = np.sin(2 * np.pi * 40 * x) + np.sin(2 * np.pi * 40 * y)
    data = low_2d + high_2d
    field = make_field(data=data, shape=None, xreal=1e-6, yreal=1e-6)

    result_lp, = node.process(field, filter_type="lowpass", cutoff=0.15, cutoff_high=0.4, order=4)
    assert result_lp.data.shape == (N, N)
    assert result_lp.xreal == field.xreal
    assert result_lp.si_unit_z == field.si_unit_z
    corr_low = np.corrcoef(result_lp.data.ravel(), low_2d.ravel())[0, 1]
    corr_high = np.corrcoef(result_lp.data.ravel(), high_2d.ravel())[0, 1]
    assert corr_low > 0.9
    assert abs(corr_high) < 0.3

    result_hp, = node.process(field, filter_type="highpass", cutoff=0.4, cutoff_high=0.4, order=4)
    assert abs(np.corrcoef(result_hp.data.ravel(), low_2d.ravel())[0, 1]) < 0.3
    assert np.corrcoef(result_hp.data.ravel(), high_2d.ravel())[0, 1] > 0.9

    const = make_field(data=np.ones((32, 32)) * 7.0)
    result_const, = node.process(const, filter_type="lowpass", cutoff=0.5, cutoff_high=0.5, order=2)
    assert np.allclose(result_const.data, 7.0, atol=1e-10)
