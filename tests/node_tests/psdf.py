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
    psdf, measurement = psdf_node.process(field, windowing="hann", level="plane")
    assert np.allclose(psdf.data, fft_psdf.data)
    assert psdf.data.shape == field.data.shape
    assert psdf.domain == "frequency"
    assert psdf.si_unit_xy == "1/m"
    assert psdf.si_unit_z == "nm^2 m^2"
    assert np.all(psdf.data >= 0.0)

    # Measurement table reports the total RMS roughness in the Z unit.
    assert isinstance(measurement, list)
    assert len(measurement) == 1
    rms_row = measurement[0]
    assert set(rms_row) == {"quantity", "value", "unit"}
    assert rms_row["quantity"] == "RMS roughness"
    assert rms_row["unit"] == "nm"
    assert rms_row["value"] > 0.0
    assert isinstance(rms_row["value"], float)

    white = DataField(
        data=np.random.default_rng(123).standard_normal((128, 128)),
        xreal=1.0e-6, yreal=1.0e-6, si_unit_xy="m", si_unit_z="m",
    )
    psdf_white, measurement_white = psdf_node.process(white, windowing="none", level="none")
    variance = float(np.var(white.data))
    dk_x = psdf_white.xreal / psdf_white.xres
    dk_y = psdf_white.yreal / psdf_white.yres
    integral = float(np.sum(psdf_white.data) * dk_x * dk_y)
    assert 0.8 < integral / variance < 1.2
    # The reported RMS roughness matches the recovered variance (Parseval).
    assert measurement_white[0]["quantity"] == "RMS roughness"
    assert measurement_white[0]["unit"] == "m"
    assert measurement_white[0]["value"] > 0.0
    assert np.isclose(measurement_white[0]["value"], float(np.std(white.data)), rtol=0.15)
