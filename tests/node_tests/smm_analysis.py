import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _make_inputs():
    """Return amplitude and phase fields suitable for SMM analysis."""
    raw = np.abs(make_field().data)
    amplitude_data = raw / raw.max() * 0.8 + 0.1
    amplitude = make_field(data=amplitude_data)
    phase = make_field()
    return amplitude, phase


def test_output_shapes():
    from backend.nodes.smm_analysis import SMMAnalysis

    node = SMMAnalysis()
    amplitude, phase = _make_inputs()
    cap, imp = node.process(
        amplitude, phase,
        frequency=1e9, ref_impedance=50.0,
        cal_c1=1e-15, cal_c2=10e-15, cal_c3=100e-15,
        cal_s11_1=0.9, cal_s11_2=0.5, cal_s11_3=0.1,
    )
    assert cap.data.shape == amplitude.data.shape
    assert imp.data.shape == amplitude.data.shape


def test_finite_outputs():
    from backend.nodes.smm_analysis import SMMAnalysis

    node = SMMAnalysis()
    amplitude, phase = _make_inputs()
    cap, imp = node.process(
        amplitude, phase,
        frequency=1e9, ref_impedance=50.0,
        cal_c1=1e-15, cal_c2=10e-15, cal_c3=100e-15,
        cal_s11_1=0.9, cal_s11_2=0.5, cal_s11_3=0.1,
    )
    assert np.isfinite(cap.data).all()
    assert np.isfinite(imp.data).all()


def test_capacitance_units():
    from backend.nodes.smm_analysis import SMMAnalysis

    node = SMMAnalysis()
    amplitude, phase = _make_inputs()
    cap, _imp = node.process(
        amplitude, phase,
        frequency=1e9, ref_impedance=50.0,
        cal_c1=1e-15, cal_c2=10e-15, cal_c3=100e-15,
        cal_s11_1=0.9, cal_s11_2=0.5, cal_s11_3=0.1,
    )
    assert cap.si_unit_z == "F"


def test_impedance_units():
    from backend.nodes.smm_analysis import SMMAnalysis

    node = SMMAnalysis()
    amplitude, phase = _make_inputs()
    _cap, imp = node.process(
        amplitude, phase,
        frequency=1e9, ref_impedance=50.0,
        cal_c1=1e-15, cal_c2=10e-15, cal_c3=100e-15,
        cal_s11_1=0.9, cal_s11_2=0.5, cal_s11_3=0.1,
    )
    assert imp.si_unit_z == "Ohm"
