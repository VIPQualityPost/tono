import numpy as np
import pytest
from tests.node_tests._shared import make_field


@pytest.fixture(scope="module")
def node():
    from backend.nodes.mfm_lift_shift import MFMLiftShift

    return MFMLiftShift()


@pytest.fixture(scope="module")
def field():
    rng = np.random.default_rng(3)
    data = np.array(
        [np.convolve(rng.standard_normal(64), np.ones(5) / 5, "same") for _ in range(48)]
    )
    return make_field(data=data, shape=(48, 64))


def test_output_arity_and_shape(node, field):
    shifted, table = node.process(field, 20e-9)
    assert shifted.data.shape == field.data.shape
    assert isinstance(table, list)
    assert len(table) == 1
    assert set(table[0]) == {"quantity", "value", "unit"}
    assert table[0]["quantity"] == "Effective lift shift"
    assert table[0]["value"] == 20e-9
    assert table[0]["unit"] == "m"


def test_metadata_preserved(node, field):
    shifted, _ = node.process(field, 20e-9)
    assert shifted.si_unit_z == field.si_unit_z
    assert shifted.si_unit_xy == field.si_unit_xy
    assert shifted.xreal == field.xreal
    assert shifted.yreal == field.yreal
    # Value units are kept (e.g. A/m MFM data stays A/m).
    am = make_field(data=field.data, shape=(48, 64))
    am.si_unit_z = "A/m"
    shifted_am, _ = node.process(am, 10e-9)
    assert shifted_am.si_unit_z == "A/m"


def test_zero_shift_is_identity(node, field):
    shifted, _ = node.process(field, 0.0)
    assert np.allclose(shifted.data, field.data, rtol=1e-12, atol=1e-12)


def test_roundtrip(node, field):
    """Shifting up by dz and back down by the same amount recovers the input."""
    up = node.process(field, 12e-9)[0]
    back = node.process(up, -12e-9)[0]
    assert np.allclose(back.data, field.data, rtol=1e-9, atol=1e-12)


def test_dc_component_preserved(node, field):
    """The transfer function equals 1 at DC, so the mean value is unchanged."""
    for dz in (10e-9, 30e-9, -5e-9):
        shifted, _ = node.process(field, dz)
        assert abs(shifted.data.mean() - field.data.mean()) < 1e-12


def test_positive_shift_blurs(node, field):
    """Away from the surface (positive dz) high frequencies are attenuated,
    which must reduce the RMS value of a zero-mean field."""
    shifted, _ = node.process(field, 30e-9)
    assert shifted.data.std() < field.data.std()


def test_negative_shift_sharpens(node, field):
    shifted, _ = node.process(field, -10e-9)
    # A tiny backwards shift must not leave the data unchanged.
    assert not np.allclose(shifted.data, field.data)


def test_sharpened_data_stays_finite(node, field):
    shifted, _ = node.process(field, -25e-9)
    assert np.isfinite(shifted.data).all()
