import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.data_types import LineData


def test_radial_profile_constant_field():
    """Constant field: profile should equal the constant at every finite bin."""
    from backend.nodes.radial_profile import RadialProfile

    node = RadialProfile()
    field = make_field(data=np.full((64, 64), 2.5))

    result, = node.process(field, cx=0.5, cy=0.5, n_bins=32)
    assert isinstance(result, LineData)
    assert len(result.data) == 32

    finite = result.data[np.isfinite(result.data)]
    assert finite.size > 0
    assert np.allclose(finite, 2.5, atol=1e-10)


def test_radial_profile_units():
    from backend.nodes.radial_profile import RadialProfile

    node = RadialProfile()
    field = make_field()

    result, = node.process(field, cx=0.5, cy=0.5, n_bins=32)
    assert result.x_unit == field.si_unit_xy
    assert result.y_unit == field.si_unit_z


def test_radial_profile_x_axis_monotone():
    """Radius axis must be strictly increasing and start near zero."""
    from backend.nodes.radial_profile import RadialProfile

    node = RadialProfile()
    field = make_field()

    result, = node.process(field, cx=0.5, cy=0.5, n_bins=64)
    assert result.x_axis[0] >= 0.0
    assert np.all(np.diff(result.x_axis) > 0)


def test_radial_profile_off_centre():
    """Off-centre origin produces a valid profile with the same number of bins."""
    from backend.nodes.radial_profile import RadialProfile

    node = RadialProfile()
    field = make_field(data=np.ones((64, 64)))

    result, = node.process(field, cx=0.0, cy=0.0, n_bins=32)
    assert len(result.data) == 32
    finite = result.data[np.isfinite(result.data)]
    assert np.allclose(finite, 1.0, atol=1e-10)


def test_radial_profile_radial_symmetry():
    """A radially symmetric field should give a smooth, non-constant profile."""
    from backend.nodes.radial_profile import RadialProfile

    node = RadialProfile()
    yres, xres = 64, 64
    ys, xs = np.mgrid[0:yres, 0:xres]
    r = np.hypot(xs - xres / 2.0, ys - yres / 2.0)
    data = np.cos(r * np.pi / (xres / 2.0))
    field = make_field(data=data)

    result, = node.process(field, cx=0.5, cy=0.5, n_bins=32)
    finite = result.data[np.isfinite(result.data)]
    # The profile should vary (not constant)
    assert np.std(finite) > 0.01


def test_radial_profile_n_bins():
    from backend.nodes.radial_profile import RadialProfile

    node = RadialProfile()
    field = make_field()

    for n in (16, 64, 256):
        result, = node.process(field, cx=0.5, cy=0.5, n_bins=n)
        assert len(result.data) == n
        assert len(result.x_axis) == n
