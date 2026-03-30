import numpy as np
from backend.data_types import LineData, RecordTable


def test_fft_1d_peak_period():
    from backend.nodes.fft_1d import FFT1D

    node = FFT1D()

    n = 256
    period = 32  # pixels
    dx = 1e-9    # 1 nm per pixel
    t = np.arange(n, dtype=np.float64)
    signal = np.sin(2 * np.pi * t / period)
    profile = LineData(
        data=signal,
        x_axis=t * dx,
        x_unit="m",
        y_unit="V",
    )

    freq_line, table = node.process(profile)

    assert isinstance(freq_line, LineData)
    assert isinstance(table, RecordTable)
    assert len(table) == 1
    assert table[0]["quantity"] == "Peak period"
    assert table[0]["unit"] == "m"

    # Peak period should be close to 32 nm
    expected = period * dx
    assert abs(table[0]["value"] - expected) / expected < 0.1

    # Output axis is in metres (spatial units)
    assert freq_line.x_unit == "m"
    # Spectrum values are non-negative magnitudes
    assert np.all(freq_line.data >= 0)
    # Highest spectral value corresponds to peak period
    peak_idx = np.argmax(freq_line.data)
    assert abs(freq_line.x_axis[peak_idx] - expected) / expected < 0.1


def test_fft_1d_no_x_axis():
    from backend.nodes.fft_1d import FFT1D

    node = FFT1D()

    # Plain numpy array without calibration — should fall back to d=1, unit="m"
    signal = np.sin(2 * np.pi * np.arange(64) / 8)
    freq_line, table = node.process(signal)

    assert isinstance(freq_line, LineData)
    assert len(freq_line.data) > 0
    assert np.all(freq_line.data >= 0)
    assert len(table) == 1


def test_fft_1d_output_length():
    from backend.nodes.fft_1d import FFT1D

    node = FFT1D()

    for n in (32, 64, 128):
        data = np.random.default_rng(n).standard_normal(n)
        profile = LineData(data=data, x_axis=np.arange(n, dtype=np.float64) * 1e-9, x_unit="m")
        freq_line, _ = node.process(profile)
        # rfft gives n//2+1 bins; DC (index 0) is removed, leaving n//2 points
        assert len(freq_line.data) == n // 2
