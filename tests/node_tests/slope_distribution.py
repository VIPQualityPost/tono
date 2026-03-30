import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.data_types import LineData


def test_slope_distribution_output_shape():
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    field = make_field()

    for dist in ("theta", "phi", "gradient"):
        result, = node.process(field, dist, 90)
        assert isinstance(result, LineData)
        assert len(result.data) == 90
        assert len(result.x_axis) == 90


def test_slope_distribution_theta_non_negative_and_normalized():
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    field = make_field()

    result, = node.process(field, "theta", 90)
    assert np.all(result.data >= 0.0)
    assert result.x_unit == "deg"
    # Probability density: integral ≈ 1  (bin_width × sum ≈ 1)
    bin_width = result.x_axis[1] - result.x_axis[0]
    integral = float(np.sum(result.data) * bin_width)
    assert abs(integral - 1.0) < 0.05


def test_slope_distribution_gradient_normalized():
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    field = make_field()

    result, = node.process(field, "gradient", 100)
    assert np.all(result.data >= 0.0)
    # Probability density: integral ≈ 1
    bin_width = result.x_axis[1] - result.x_axis[0]
    integral = float(np.sum(result.data) * bin_width)
    assert abs(integral - 1.0) < 0.05


def test_slope_distribution_phi_units():
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    field = make_field()

    result, = node.process(field, "phi", 180)
    assert result.x_unit == "deg"
    assert np.all(result.data >= 0.0)
    # x-axis must span [0, 360)
    assert result.x_axis[0] >= 0.0
    assert result.x_axis[-1] < 360.0


def test_slope_distribution_flat_field_theta():
    """Flat field: all gradients are zero → theta=0 everywhere, first bin gets all weight."""
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    field = make_field(data=np.zeros((32, 32)))

    result, = node.process(field, "theta", 90)
    # With max_theta=0 we use fallback 90; all pixels land in bin 0
    assert result.data[0] == pytest.approx(result.data.sum(), abs=1e-10)


def test_slope_distribution_x_ramp_phi():
    """X-only ramp: slope direction should be concentrated near phi=180° (ascending left, or 0°/360°)."""
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    data = np.tile(np.linspace(0.0, 1.0, 64), (64, 1))
    field = make_field(data=data)

    result, = node.process(field, "phi", 360)
    # Peak should be within first or last few bins (phi ≈ 0 or 2π, i.e., ascending in +x direction)
    # atan2(0, -gx) with gx>0 gives atan2(0,-gx) = π, so peak near 180°
    peak_idx = int(np.argmax(result.data))
    peak_deg = float(result.x_axis[peak_idx])
    assert 150.0 < peak_deg < 210.0, f"Unexpected peak at {peak_deg}°"


def test_slope_distribution_unknown_distribution():
    from backend.nodes.slope_distribution import SlopeDistribution

    node = SlopeDistribution()
    field = make_field()

    with pytest.raises(ValueError):
        node.process(field, "azimuth", 90)
