import numpy as np


def test_fft_filter_1d():
    from backend.nodes.filter_fft_1d import FFTFilter1D
    node = FFTFilter1D()

    n = 256
    t = np.arange(n, dtype=np.float64) / n
    low = np.sin(2 * np.pi * 3 * t)
    high = np.sin(2 * np.pi * 80 * t)
    line = low + high

    filtered_lp, = node.process(line, filter_type="lowpass", cutoff=0.15, cutoff_high=0.4, order=4)
    assert len(filtered_lp) == n
    corr_low = np.corrcoef(filtered_lp, low)[0, 1]
    corr_high = np.corrcoef(filtered_lp, high)[0, 1]
    assert corr_low > 0.95
    assert abs(corr_high) < 0.3

    filtered_hp, = node.process(line, filter_type="highpass", cutoff=0.4, cutoff_high=0.4, order=4)
    corr_low_hp = np.corrcoef(filtered_hp, low)[0, 1]
    corr_high_hp = np.corrcoef(filtered_hp, high)[0, 1]
    assert abs(corr_low_hp) < 0.3
    assert corr_high_hp > 0.95

    filtered_bp, = node.process(line, filter_type="bandpass", cutoff=0.4, cutoff_high=0.8, order=4)
    assert abs(np.corrcoef(filtered_bp, low)[0, 1]) < 0.3
    assert np.corrcoef(filtered_bp, high)[0, 1] > 0.9

    filtered_notch, = node.process(line, filter_type="notch", cutoff=0.4, cutoff_high=0.8, order=4)
    assert np.corrcoef(filtered_notch, low)[0, 1] > 0.95
    assert abs(np.corrcoef(filtered_notch, high)[0, 1]) < 0.3
