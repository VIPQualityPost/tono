"""Tests for the Angle Distribution node."""

import numpy as np
import pytest

from backend.data_types import DataField
from backend.nodes.angle_distribution import _filter_slope, _fit_local_plane_slopes


def _plane_field(shape=(64, 64), a=1e-9, b=2e-9, dx=1e-7):
    yres, xres = shape
    ky, kx = np.mgrid[0:yres, 0:xres]
    data = a * kx + b * ky
    return DataField(data=data, xreal=xres * dx, yreal=yres * dx, si_unit_xy="m", si_unit_z="m")


def test_outputs_arity():
    from backend.nodes.angle_distribution import AngleDistribution

    assert len(AngleDistribution.OUTPUTS) == 2
    dist, table = AngleDistribution().process(_plane_field(), size=64, steps=180,
                                              logscale=False, fit_plane=False, kernel_size=5)
    assert isinstance(table, list) and len(table) == 3


def test_filter_slope_exact_for_plane():
    """Symmetric differences reproduce the plane slope exactly everywhere (the
    value check is numerically exact, not a tolerance)."""
    field = _plane_field()
    xder, yder = _filter_slope(field.data, field.dx, field.dy)
    assert np.allclose(xder, 1e-9 / 1e-7, rtol=1e-12)
    assert np.allclose(yder, 2e-9 / 1e-7, rtol=1e-12)


def test_local_plane_fit_exact_interior():
    """Plane fitting is exact for centerd windows; edge windows are
    clamped and only approximately centerd."""
    field = _plane_field()
    xder, yder = _fit_local_plane_slopes(field.data, 5, field.dx, field.dy)
    interior = (slice(6, 58), slice(6, 58))
    assert np.allclose(xder[interior], 0.01, rtol=1e-12)
    assert np.allclose(yder[interior], 0.02, rtol=1e-12)
    # Mean over all pixels stays within 5% of the exact plane slope angle.
    d = np.arctan(np.hypot(xder, yder))
    assert abs(d.mean() - 0.022356954) < 0.05 * 0.022356954


def test_plane_mass_conservation_and_measurements():
    from backend.nodes.angle_distribution import AngleDistribution

    field = _plane_field()
    dist, table = AngleDistribution().process(field, size=64, steps=180, logscale=False,
                                              fit_plane=False, kernel_size=5)
    # Every pixel deposits one vote per step.
    assert int(dist.data.sum()) == 64 * 64 * 180
    assert dist.data.shape == (64, 64)
    assert np.all(dist.data >= 0.0)
    # Mean slope angle is the exact plane angle, maximal angle matches.
    expected = float(np.arctan(np.hypot(1e-9, 2e-9) / 1e-7))
    assert np.isclose(table[0]["value"], expected, atol=1e-12)
    assert np.isclose(table[1]["value"], 0.0, atol=1e-9)  # plane: zero spread
    assert np.isclose(table[2]["value"], expected, atol=1e-12)
    for row in table:
        assert set(row) == {"quantity", "value", "unit"}
        assert row["unit"] == "rad"


def test_distribution_metadata():
    from backend.nodes.angle_distribution import AngleDistribution

    dist, _ = AngleDistribution().process(_plane_field(), size=100, steps=72, logscale=False,
                                          fit_plane=False, kernel_size=5)
    assert dist.data.shape == (100, 100)
    assert dist.si_unit_xy == "rad"
    assert dist.si_unit_z == ""
    assert np.isclose(dist.xreal, 2 * np.pi)
    assert np.isclose(dist.yreal, 2 * np.pi)
    assert np.isclose(dist.xoff, -np.pi)
    assert np.isclose(dist.yoff, -np.pi)


def test_logscale_mapping():
    from backend.nodes.angle_distribution import AngleDistribution

    node = AngleDistribution()
    lin, _ = node.process(_plane_field(), size=64, steps=90, logscale=False,
                          fit_plane=False, kernel_size=5)
    log, _ = node.process(_plane_field(), size=64, steps=90, logscale=True,
                          fit_plane=False, kernel_size=5)
    with np.errstate(divide="ignore"):
        expected = np.where(lin.data > 0.0, np.log(lin.data) + 1.0, 0.0)
    assert np.allclose(log.data, expected)
    assert np.all(log.data >= 0.0)


def test_constant_field_yields_zero_distribution():
    from backend.nodes.angle_distribution import AngleDistribution

    field = DataField(data=np.ones((32, 32)) * 3.0, xreal=32e-7, yreal=32e-7,
                      si_unit_xy="m", si_unit_z="m")
    dist, table = AngleDistribution().process(field, size=32, steps=90, logscale=False,
                                              fit_plane=False, kernel_size=5)
    assert dist.data.sum() == 0.0
    assert all(row["value"] == 0.0 for row in table)


def test_fit_plane_flow_runs():
    from backend.nodes.angle_distribution import AngleDistribution

    dist, table = AngleDistribution().process(_plane_field(), size=64, steps=180, logscale=False,
                                              fit_plane=True, kernel_size=5)
    assert int(dist.data.sum()) == 64 * 64 * 180
    assert table[0]["value"] > 0.0


def test_invalid_size_raises():
    from backend.nodes.angle_distribution import AngleDistribution

    with pytest.raises(ValueError, match="at least 1"):
        AngleDistribution().process(_plane_field(), size=0, steps=90, logscale=False,
                                    fit_plane=False, kernel_size=5)
