import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _make_node():
    from backend.nodes.radial_smoothing import RadialSmoothing
    return RadialSmoothing()


def _radial_bump(shape=(64, 64), peak=1.0, sigma=8.0):
    """Rotationally symmetric Gaussian bump centred on the image centre pixel."""
    yres, xres = shape
    yy, xx = np.mgrid[0:yres, 0:xres]
    r = np.sqrt((xx - xres / 2.0) ** 2 + (yy - yres / 2.0) ** 2)
    return peak * np.exp(-(r ** 2) / (2.0 * sigma ** 2))


def _radius_grid(shape=(64, 64)):
    yres, xres = shape
    yy, xx = np.mgrid[0:yres, 0:xres]
    return np.sqrt((xx - xres / 2.0) ** 2 + (yy - yres / 2.0) ** 2)


def test_output_arity():
    node = _make_node()
    assert len(node.OUTPUTS) == 1
    assert node.OUTPUTS[0][0] == "DATA_FIELD"
    field = make_field(data=_radial_bump())
    result = node.process(field, sigma_r=3.0, sigma_phi_deg=5.0, interpolation="linear")
    assert isinstance(result, tuple) and len(result) == 1


def test_output_shape_and_metadata_preserved():
    node = _make_node()
    field = make_field(data=_radial_bump(), xreal=2e-6, yreal=3e-6)
    (smooth,) = node.process(field, sigma_r=4.0, sigma_phi_deg=7.0, interpolation="linear")
    assert smooth.data.shape == field.data.shape
    assert smooth.xres == field.xres and smooth.yres == field.yres
    assert smooth.xreal == pytest.approx(field.xreal)
    assert smooth.yreal == pytest.approx(field.yreal)
    assert smooth.xoff == field.xoff and smooth.yoff == field.yoff
    assert smooth.si_unit_xy == field.si_unit_xy
    assert smooth.si_unit_z == field.si_unit_z


def test_zero_sigmas_close_to_identity_interior():
    """With no smoothing the polar round trip only shifts smooth data by about
    half a pixel, so on the interior the field comes back nearly unchanged.
    (Pixels within a pixel of the corners exceed the polar radius grid; there
    the C code's periodic radial extension mixes the field centre in.)"""
    node = _make_node()
    data = _radial_bump()
    field = make_field(data=data)
    interior = _radius_grid() <= 43.0
    tolerances = {"linear": 0.05, "cubic": 0.05, "nearest": 0.12}
    for interp, atol in tolerances.items():
        (smooth,) = node.process(field, sigma_r=0.0, sigma_phi_deg=0.0,
                                 interpolation=interp)
        assert np.allclose(smooth.data[interior], data[interior], atol=atol), interp


def test_corner_pixels_read_centre_value():
    """Faithful to raveraging.c: the polar field is extended periodically along
    the radius, so corner pixels (radius beyond the polar grid) interpolate
    towards the centre column and read a large value."""
    node = _make_node()
    data = _radial_bump()
    field = make_field(data=data)
    (smooth,) = node.process(field, sigma_r=0.0, sigma_phi_deg=0.0,
                             interpolation="linear")
    assert smooth.data[0, 0] > 0.5          # corner mixes in the centre value
    assert data[0, 0] < 1e-6                 # the input corner is negligible


def test_angular_smoothing_preserves_rotational_symmetry():
    """Angular (rotational) smoothing of a rotationally symmetric field must
    leave every point on a circle of constant radius (nearly) equal."""
    node = _make_node()
    data = _radial_bump(sigma=12.0)
    field = make_field(data=data)
    (smooth,) = node.process(field, sigma_r=0.0, sigma_phi_deg=40.0,
                             interpolation="linear")
    for r in (4, 9, 16, 24):
        p1, p2, p3 = (32 + r, 32), (32, 32 + r), (32 - r, 32)
        vals = [smooth.data[p] for p in (p1, p2, p3)]
        assert max(vals) - min(vals) < 1e-3, (r, vals)


def test_radial_smoothing_reduces_bump_peak():
    """Radial smoothing blurs the radial profile, so the bump peak drops."""
    node = _make_node()
    data = _radial_bump(peak=1.0, sigma=8.0)
    field = make_field(data=data)
    (smooth,) = node.process(field, sigma_r=6.0, sigma_phi_deg=0.0,
                             interpolation="linear")
    assert smooth.data[32, 32] < data[32, 32] - 0.1   # peak clearly reduced
    assert smooth.data.max() < data.max()


def test_angular_smoothing_spreads_offcentre_blob():
    """Angular smoothing moves mass along the circle of constant radius: an
    off-centre blob is smeared over an arc, reducing its peak and raising the
    value at an angularly separated point on the same circle."""
    node = _make_node()
    data = np.zeros((64, 64))
    yy, xx = np.mgrid[0:64, 0:64]
    data += np.exp(-((xx - (32 + 9)) ** 2 + (yy - 32) ** 2) / (2.0 * 3.0 ** 2))
    field = make_field(data=data)
    (smooth,) = node.process(field, sigma_r=0.0, sigma_phi_deg=120.0,
                             interpolation="linear")
    assert smooth.data[32, 41] < data[32, 41] * 0.5     # peak much reduced
    assert smooth.data[32, 23] > 0.05                    # far point gained mass


def test_smoothing_reduces_noise_rms():
    """Both-direction smoothing of a noisy field reduces its RMS roughness."""
    node = _make_node()
    rng = np.random.default_rng(3)
    base = _radial_bump()
    data = base + 0.1 * rng.standard_normal(base.shape)
    field = make_field(data=data)
    (smooth,) = node.process(field, sigma_r=4.0, sigma_phi_deg=20.0,
                             interpolation="linear")
    assert np.std(smooth.data) < np.std(data)


def test_cubic_interpolation_runs():
    node = _make_node()
    field = make_field(data=_radial_bump(sigma=12.0))
    (smooth,) = node.process(field, sigma_r=2.0, sigma_phi_deg=3.0,
                             interpolation="cubic")
    assert smooth.data.shape == field.data.shape
    assert np.isfinite(smooth.data).all()


def test_invalid_interpolation_raises():
    node = _make_node()
    field = make_field()
    with pytest.raises(ValueError):
        node.process(field, sigma_r=1.0, sigma_phi_deg=1.0, interpolation="bogus")


def test_negative_sigma_raises():
    node = _make_node()
    field = make_field()
    with pytest.raises(ValueError):
        node.process(field, sigma_r=-1.0, sigma_phi_deg=1.0, interpolation="linear")
