import numpy as np
from tests.node_tests._shared import make_field


def test_fft2d():
    from backend.nodes.fft_2d import FFT2D

    node = FFT2D()

    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    freq = 5
    data = np.sin(2 * np.pi * freq * x)
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    spectrum, spec_mag, spec_phase, spec_psdf = node.process(field, windowing="none", level="none")
    assert spectrum.data.shape == (N, N)
    assert spectrum.domain == "frequency"
    assert spectrum.si_unit_xy == "1/m"
    center = N // 2
    row = spectrum.data[center, :]
    peak_idx = np.argmax(row[center + 1:]) + center + 1
    assert abs(peak_idx - (center + freq)) <= 1, f"Peak at {peak_idx}, expected ~{center + freq}"

    _, spec_mag, _, _ = node.process(field, windowing="hann", level="mean")
    assert spec_mag.data.shape == (N, N)
    assert np.all(spec_mag.data >= 0)

    _, _, spec_phase, _ = node.process(field, windowing="none", level="none")
    assert spec_phase.data.shape == (N, N)
    assert spec_phase.data.min() >= -np.pi - 0.01
    assert spec_phase.data.max() <= np.pi + 0.01

    _, _, _, spec_psdf = node.process(field, windowing="hamming", level="plane")
    assert spec_psdf.data.shape == (N, N)
    assert np.all(spec_psdf.data >= 0)
    assert "^2" in spec_psdf.si_unit_z

    const_field = make_field(data=np.ones((32, 32)) * 3.0)
    _, spec_const, _, _ = node.process(const_field, windowing="none", level="none")
    center32 = 16
    dc_val = spec_const.data[center32, center32]
    assert dc_val == spec_const.data.max()

    spec_bk, _, _, _ = node.process(field, windowing="blackman", level="none")
    assert spec_bk.data.shape == (N, N)
