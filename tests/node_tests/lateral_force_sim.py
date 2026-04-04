import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shapes():
    """Both forward and reverse outputs must have the same shape as the input."""
    from backend.nodes.lateral_force_sim import LateralForceSim

    node = LateralForceSim()
    field = make_field(shape=(48, 64))

    for direction in ("forward", "reverse", "both"):
        fwd, rev = node.process(field, direction, 0.3, 1e-9, 10e-9)
        assert fwd.data.shape == field.data.shape, f"forward shape mismatch for direction={direction}"
        assert rev.data.shape == field.data.shape, f"reverse shape mismatch for direction={direction}"


def test_flat_surface_uniform():
    """A flat (constant) topography has zero slope everywhere, so the lateral
    force should be spatially uniform (pure friction, no topographic component)."""
    from backend.nodes.lateral_force_sim import LateralForceSim

    node = LateralForceSim()
    data = np.full((32, 32), 5e-9, dtype=np.float64)
    field = make_field(data=data)

    fwd, rev = node.process(field, "both", 0.3, 1e-9, 10e-9)

    # All values in each output should be identical (uniform)
    assert np.ptp(fwd.data) < 1e-20, "Forward lateral force is not uniform on flat surface"
    assert np.ptp(rev.data) < 1e-20, "Reverse lateral force is not uniform on flat surface"


def test_forward_reverse_different():
    """For a non-flat surface with 'both' direction, forward and reverse
    lateral force signals should differ (topographic artifact is direction-dependent)."""
    from backend.nodes.lateral_force_sim import LateralForceSim

    node = LateralForceSim()
    # Create a steep ramp in x so there is a significant slope
    ramp = np.tile(np.linspace(0.0, 500e-9, 64), (64, 1))
    field = make_field(data=ramp)

    fwd, rev = node.process(field, "both", 0.3, 1e-9, 10e-9)

    # Forward and reverse differ due to slope-dependent asymmetry;
    # use strict tolerance to detect the difference at nanoNewton scale.
    assert not np.allclose(fwd.data, rev.data, atol=0, rtol=1e-6), (
        "Forward and reverse should differ on a sloped surface"
    )


def test_finite_values():
    """All output values must be finite (no NaN or inf) for typical inputs."""
    from backend.nodes.lateral_force_sim import LateralForceSim

    node = LateralForceSim()
    field = make_field()  # random topography

    for direction in ("forward", "reverse", "both"):
        fwd, rev = node.process(field, direction, 0.3, 1e-9, 10e-9)
        assert np.isfinite(fwd.data).all(), f"Non-finite values in forward output (direction={direction})"
        assert np.isfinite(rev.data).all(), f"Non-finite values in reverse output (direction={direction})"
