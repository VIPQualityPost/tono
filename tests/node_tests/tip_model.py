import numpy as np
import pytest
from tests.node_tests._shared import make_field


def make_tip(shape="parabola", radius=10e-9, half_angle=20.0, n_pixels=65, field=None):
    from backend.nodes.tip_model import TipModel
    if field is None:
        # 1 nm/pixel reference field
        field = make_field(shape=(128, 128), xreal=128e-9, yreal=128e-9)
    node = TipModel()
    result, = node.process(field=field, shape=shape, radius=radius,
                           half_angle=half_angle, n_pixels=n_pixels)
    return result


# ── Shape and dimensionality ────────────────────────────────────────────────

def test_tip_output_is_data_field():
    from backend.data_types import DataField
    tip = make_tip()
    assert isinstance(tip, DataField)


def test_tip_shape_matches_n_pixels():
    """Output grid must be (n_pixels, n_pixels)."""
    for n in (5, 9, 33, 65):
        tip = make_tip(n_pixels=n)
        assert tip.data.shape == (n, n)


def test_tip_n_pixels_even_forced_odd():
    """Even n_pixels should be silently bumped to n+1."""
    tip = make_tip(n_pixels=64)
    assert tip.data.shape[0] % 2 == 1
    assert tip.data.shape[0] == 65


def test_tip_xreal_equals_n_times_pixel_size():
    """xreal must equal n_pixels * pixel_size of the reference field."""
    pixel_size = 1e-9
    field = make_field(shape=(128, 128), xreal=128 * pixel_size, yreal=128 * pixel_size)
    tip = make_tip(n_pixels=65, field=field)
    assert abs(tip.xreal - 65 * pixel_size) < 1e-25


def test_tip_units_inherited_from_field():
    field = make_field()
    field.si_unit_xy = "nm"
    field.si_unit_z = "V"
    tip = make_tip(field=field)
    assert tip.si_unit_xy == "nm"
    assert tip.si_unit_z == "V"


# ── Apex and minimum conventions ────────────────────────────────────────────

@pytest.mark.parametrize("shape", ["parabola", "cone", "sphere"])
def test_tip_min_is_zero(shape):
    """All shapes must shift the data so the minimum is 0."""
    tip = make_tip(shape=shape)
    assert tip.data.min() >= -1e-15


@pytest.mark.parametrize("shape", ["parabola", "cone", "sphere"])
def test_tip_apex_at_centre(shape):
    """Centre pixel must equal the maximum for all shapes."""
    tip = make_tip(shape=shape)
    n = tip.data.shape[0]
    ci = n // 2
    assert tip.data[ci, ci] == pytest.approx(tip.data.max(), abs=1e-20)


@pytest.mark.parametrize("shape", ["parabola", "cone", "sphere"])
def test_tip_radial_symmetry(shape):
    """All shapes must be left-right and up-down symmetric."""
    tip = make_tip(shape=shape)
    data = tip.data
    assert np.allclose(data, np.flipud(data), atol=1e-12)
    assert np.allclose(data, np.fliplr(data), atol=1e-12)


# ── Parabola formula verification ────────────────────────────────────────────

def test_parabola_apex_formula():
    """Parabola apex height = (half_width)² / R (z0 = 2a·x_half²)."""
    radius = 20e-9
    n = 65
    pixel_size = 1e-9
    field = make_field(shape=(256, 256), xreal=256 * pixel_size, yreal=256 * pixel_size)
    tip = make_tip(shape="parabola", radius=radius, n_pixels=n, field=field)

    x_half = (n // 2) * pixel_size    # = 32 nm
    expected_apex = x_half**2 / radius # = 1024e-18 / 20e-9 = 51.2 nm
    assert abs(tip.data[n // 2, n // 2] - expected_apex) < 1e-12 * expected_apex


def test_parabola_decreases_monotonically_from_centre():
    """Parabola row profile must be monotonically decreasing from centre outward."""
    tip = make_tip(shape="parabola", n_pixels=33)
    ci = 16
    row = tip.data[ci, :]
    assert np.all(np.diff(row[:ci + 1]) >= 0)   # left half increases toward centre
    assert np.all(np.diff(row[ci:]) <= 0)        # right half decreases from centre


def test_parabola_corner_value_is_zero():
    """z0 is constructed so that z at (±half, ±half) = 0 exactly."""
    n = 33
    tip = make_tip(shape="parabola", n_pixels=n)
    corner = tip.data[0, 0]
    # The corner is by construction the minimum; after the min-shift it should be ~0
    assert abs(corner) < 1e-15 * tip.data[n // 2, n // 2]


# ── Cone shape ──────────────────────────────────────────────────────────────

def test_cone_apex_greater_than_edges():
    tip = make_tip(shape="cone", half_angle=20.0, n_pixels=33)
    ci = 16
    assert tip.data[ci, ci] > tip.data[0, 0]
    assert tip.data[0, 0] >= -1e-15   # edges should be ~0


def test_cone_decreases_away_from_centre():
    """Cone must be monotonically decreasing along any radial line from centre."""
    tip = make_tip(shape="cone", half_angle=20.0, n_pixels=33)
    ci = 16
    row = tip.data[ci, :]
    assert np.all(np.diff(row[ci:]) <= 0)


def test_cone_different_half_angles_differ():
    """Tips with different half-angles must produce different shapes."""
    tip_wide = make_tip(shape="cone", half_angle=40.0, n_pixels=33)
    tip_narrow = make_tip(shape="cone", half_angle=10.0, n_pixels=33)
    assert not np.allclose(tip_wide.data, tip_narrow.data)


# ── Sphere shape ─────────────────────────────────────────────────────────────

def test_sphere_curvature_near_apex():
    """Near the apex the sphere cap gives z ≈ sqrt(R²-r²), so
    z[ci,ci] - z[ci, ci+1] ≈ pixel_size² / (2R) for r << R."""
    radius = 100e-9
    pixel_size = 1e-9
    field = make_field(shape=(256, 256), xreal=256 * pixel_size, yreal=256 * pixel_size)
    tip = make_tip(shape="sphere", radius=radius, n_pixels=33, field=field)
    ci = 16
    delta_z = tip.data[ci, ci] - tip.data[ci, ci + 1]
    expected = pixel_size**2 / (2 * radius)
    # relative tolerance 0.1% (small-angle approximation holds well for r << R)
    assert abs(delta_z - expected) / expected < 1e-3
