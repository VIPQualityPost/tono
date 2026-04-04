import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_mfm_all_operations():
    from backend.nodes.mfm_analysis import MFMAnalysis

    node = MFMAnalysis()
    field = make_field(shape=(32, 32))

    for op in ("phase_to_force_gradient", "force_gradient_to_field",
               "charge_density", "magnetisation"):
        result, = node.process(field, op, 50e-9)
        assert result.data.shape == (32, 32)
        assert np.isfinite(result.data).all()


def test_mfm_flat_field():
    from backend.nodes.mfm_analysis import MFMAnalysis

    node = MFMAnalysis()
    field = make_field(data=np.zeros((32, 32)))
    result, = node.process(field, "phase_to_force_gradient", 50e-9)
    assert np.allclose(result.data, 0.0, atol=1e-10)


def test_mfm_units():
    from backend.nodes.mfm_analysis import MFMAnalysis

    node = MFMAnalysis()
    field = make_field(shape=(32, 32))

    result, = node.process(field, "force_gradient_to_field", 50e-9)
    assert result.si_unit_z == "A/m"

    result, = node.process(field, "charge_density", 50e-9)
    assert result.si_unit_z == "A/m²"


def test_mfm_unknown_operation():
    from backend.nodes.mfm_analysis import MFMAnalysis

    node = MFMAnalysis()
    field = make_field(shape=(32, 32))
    with pytest.raises(ValueError):
        node.process(field, "unknown_op", 50e-9)
