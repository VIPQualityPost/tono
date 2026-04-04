import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shapes():
    from backend.nodes.pfm_analysis import PFMAnalysis

    node = PFMAnalysis()
    vpfm_amp = make_field(data=np.abs(make_field(shape=(48, 64)).data), shape=(48, 64))
    lpfm_amp = make_field(data=np.abs(make_field(shape=(48, 64)).data), shape=(48, 64))
    vpfm_phase = make_field(shape=(48, 64))
    lpfm_phase = make_field(shape=(48, 64))

    magnitude, azimuth, inclination = node.process(
        vpfm_amp, lpfm_amp, vpfm_phase, lpfm_phase, "3d", 1.0,
    )

    assert magnitude.data.shape == (48, 64)
    assert azimuth.data.shape == (48, 64)
    assert inclination.data.shape == (48, 64)


def test_2d_mode_zero_inclination():
    from backend.nodes.pfm_analysis import PFMAnalysis

    node = PFMAnalysis()
    vpfm_amp = make_field(data=np.abs(make_field().data))
    lpfm_amp = make_field(data=np.abs(make_field().data))
    vpfm_phase = make_field()
    lpfm_phase = make_field()

    magnitude, azimuth, inclination = node.process(
        vpfm_amp, lpfm_amp, vpfm_phase, lpfm_phase, "2d", 1.0,
    )

    assert np.allclose(inclination.data, 0.0)


def test_3d_mode_nonzero_inclination():
    from backend.nodes.pfm_analysis import PFMAnalysis

    node = PFMAnalysis()
    vpfm_amp = make_field(data=np.abs(make_field().data))
    lpfm_amp = make_field(data=np.abs(make_field().data))
    vpfm_phase = make_field()
    lpfm_phase = make_field()

    magnitude, azimuth, inclination = node.process(
        vpfm_amp, lpfm_amp, vpfm_phase, lpfm_phase, "3d", 1.0,
    )

    assert not np.allclose(inclination.data, 0.0)


def test_magnitude_nonnegative():
    from backend.nodes.pfm_analysis import PFMAnalysis

    node = PFMAnalysis()
    vpfm_amp = make_field(data=np.abs(make_field().data))
    lpfm_amp = make_field(data=np.abs(make_field().data))
    vpfm_phase = make_field()
    lpfm_phase = make_field()

    for mode in ("2d", "3d"):
        magnitude, azimuth, inclination = node.process(
            vpfm_amp, lpfm_amp, vpfm_phase, lpfm_phase, mode, 1.0,
        )
        assert np.all(magnitude.data >= 0.0)
