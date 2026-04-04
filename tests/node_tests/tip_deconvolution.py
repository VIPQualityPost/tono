import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.data_types import DataField


def run_deconv(field, tip):
    from backend.nodes.tip_deconvolution import TipDeconvolution
    node = TipDeconvolution()
    result, = node.process(field=field, tip=tip)
    return result


def make_tip(shape="parabola", radius=10e-9, half_angle=20.0, n_pixels=33):
    from backend.nodes.tip_model import TipModel
    field = make_field(shape=(64, 64), xreal=64e-9, yreal=64e-9)
    node = TipModel()
    result, = node.process(field=field, shape=shape, radius=radius,
                           half_angle=half_angle, n_pixels=n_pixels)
    return result


# ── Output type and shape ────────────────────────────────────────────────────

def test_deconv_output_is_data_field():
    field = make_field()
    tip = DataField(data=np.zeros((1, 1)), xreal=1e-9, yreal=1e-9)
    result = run_deconv(field, tip)
    assert isinstance(result, DataField)


def test_deconv_output_shape_matches_input():
    field = make_field(shape=(64, 64))
    tip = make_tip(n_pixels=11)
    result = run_deconv(field, tip)
    assert result.data.shape == field.data.shape


def test_deconv_preserves_physical_dimensions():
    field = make_field(xreal=2e-6, yreal=3e-6)
    tip = DataField(data=np.zeros((1, 1)), xreal=1e-9, yreal=1e-9)
    result = run_deconv(field, tip)
    assert result.xreal == field.xreal
    assert result.yreal == field.yreal


def test_deconv_preserves_units():
    field = make_field()
    field.si_unit_xy = "nm"
    field.si_unit_z = "V"
    tip = DataField(data=np.zeros((1, 1)), xreal=1e-9, yreal=1e-9)
    result = run_deconv(field, tip)
    assert result.si_unit_xy == "nm"
    assert result.si_unit_z == "V"


# ── Identity with a point tip ────────────────────────────────────────────────

def test_deconv_point_tip_is_identity():
    """A 1×1 tip with value 0 is the identity: erosion with structure [[0]] = original."""
    field = make_field(data=np.random.default_rng(0).standard_normal((32, 32)) + 10)
    tip = DataField(data=np.zeros((1, 1)), xreal=1e-9, yreal=1e-9)
    result = run_deconv(field, tip)
    assert np.allclose(result.data, field.data, atol=1e-12)


# ── Flat field invariance ────────────────────────────────────────────────────

@pytest.mark.parametrize("shape", ["parabola", "cone", "sphere"])
def test_deconv_flat_field_stays_flat(shape):
    """Deconvolution of a constant-valued field must remain constant."""
    flat_data = np.full((64, 64), 5.0)
    field = make_field(data=flat_data)
    tip = make_tip(shape=shape, n_pixels=15)
    result = run_deconv(field, tip)
    interior = result.data[8:-8, 8:-8]   # avoid border effects
    assert np.allclose(interior, 5.0, atol=1e-10)


# ── Deconvolution sharpens features ─────────────────────────────────────────

def test_deconv_sharpens_broadened_image():
    """
    Forward tip dilation broadens a spike; deconvolution (erosion) should remove
    the broadening.  Result must be ≤ input everywhere (erosion is a lower bound).
    """
    from scipy.ndimage import grey_dilation

    # Build a field with a single spike
    data = np.zeros((64, 64))
    data[32, 32] = 1.0
    field = make_field(data=data)

    # Create a small parabolic tip
    tip = make_tip(shape="parabola", radius=50e-9, n_pixels=11)
    tip_data = tip.data

    # Simulate measured image via tip dilation (Gwyddion gwy_tip_dilation):
    #   dilation_tip = tip - max(tip)   (max shifted to 0, values ≤ 0)
    #   measured[y,x] = max_{ty,tx}[surface[y-ty, x-tx] + dilation_tip[ty,tx]]
    dilation_struct = tip_data - tip_data.max()
    measured_data = grey_dilation(data, structure=dilation_struct)
    measured = make_field(data=measured_data)

    # Deconvolve
    result = run_deconv(measured, tip)

    # Erosion is a lower bound on the input
    assert np.all(result.data <= measured_data + 1e-10)

    # The spike should be recovered: result at spike position ≥ most surroundings
    assert result.data[32, 32] > result.data[32, 36]


def test_deconv_erosion_never_exceeds_input():
    """Grey erosion is always ≤ the input (fundamental morphological property)."""
    field = make_field(data=np.abs(np.random.default_rng(7).standard_normal((32, 32))))
    tip = make_tip(shape="parabola", n_pixels=7)
    result = run_deconv(field, tip)
    assert np.all(result.data <= field.data + 1e-10)
