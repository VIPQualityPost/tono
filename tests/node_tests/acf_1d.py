import numpy as np
from backend.data_types import LineData, RecordTable


def test_acf_1d():
    from backend.nodes.acf_1d import ACF1D

    node = ACF1D()

    # Periodic signal — ACF should show a peak at the period
    n = 256
    period = 32
    t = np.arange(n, dtype=np.float64)
    signal = np.sin(2 * np.pi * t / period)
    profile = LineData(
        data=signal,
        x_axis=t * 1e-9,
        x_unit="m",
        y_unit="V",
    )

    acf, measurement = node.process(profile, level="mean")

    assert isinstance(acf, LineData)
    assert isinstance(measurement, RecordTable)

    # Only positive lags are output
    assert acf.x_axis is not None
    assert np.all(acf.x_axis > 0)

    # ACF should be monotonically decreasing at the very start (falls from the zero-lag peak)
    assert acf.data[0] > 0

    # Peak period should be close to the input period in metres
    expected_period_m = period * 1e-9
    assert len(measurement) == 1
    assert measurement[0]["quantity"] == "Peak period"
    assert abs(measurement[0]["value"] - expected_period_m) / expected_period_m < 0.1
    assert measurement[0]["unit"] == "m"


def test_acf_1d_no_peak():
    from backend.nodes.acf_1d import ACF1D

    node = ACF1D()

    # White noise — ACF should have no reliable peak, measurement table may be empty
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(64)
    profile = LineData(data=noise, x_axis=np.arange(64, dtype=np.float64), x_unit="m")

    acf, measurement = node.process(profile, level="none")
    assert isinstance(acf, LineData)
    # measurement is either empty or has one row — no assertion on content


def test_acf_1d_level_none():
    from backend.nodes.acf_1d import ACF1D

    node = ACF1D()

    # With level="none", a DC offset should not be removed
    data = np.ones(32, dtype=np.float64) * 5.0
    profile = LineData(data=data, x_axis=np.arange(32, dtype=np.float64))

    acf, _ = node.process(profile, level="none")
    # ACF of a constant is a constant — first positive-lag value should be positive
    assert acf.data[0] > 0
