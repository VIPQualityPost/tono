import numpy as np
from backend.data_types import DataField


def test_psdf_node():
    from backend.nodes.fft_2d import FFT2D
    from backend.nodes.psdf import PSDF

    field = DataField(
        data=np.random.default_rng(17).standard_normal((64, 64)),
        xreal=2.0e-6, yreal=1.0e-6, si_unit_xy="m", si_unit_z="nm",
    )

    fft_node = FFT2D()
    psdf_node = PSDF()

    fft_psdf = fft_node.process(field, windowing="hann", level="plane")[3]
    psdf, = psdf_node.process(field, windowing="hann", level="plane")
    assert np.allclose(psdf.data, fft_psdf.data)
    assert psdf.data.shape == field.data.shape
    assert psdf.domain == "frequency"
    assert psdf.si_unit_xy == "1/m"
    assert psdf.si_unit_z == "nm^2 m^2"
    assert np.all(psdf.data >= 0.0)

    white = DataField(
        data=np.random.default_rng(123).standard_normal((128, 128)),
        xreal=1.0e-6, yreal=1.0e-6, si_unit_xy="m", si_unit_z="m",
    )
    psdf_white, = psdf_node.process(white, windowing="none", level="none")
    variance = float(np.var(white.data))
    dk_x = psdf_white.xreal / psdf_white.xres
    dk_y = psdf_white.yreal / psdf_white.yres
    integral = float(np.sum(psdf_white.data) * dk_x * dk_y)
    assert 0.8 < integral / variance < 1.2
