import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shape():
    """Output shape should match input shape."""
    from backend.nodes.shade import Shade

    node = Shade()
    field = make_field(shape=(64, 64))
    result, = node.process(field, azimuth=315.0, elevation=45.0, blend=0.5)
    assert result.data.shape == field.data.shape


def test_output_range():
    """With blend=1.0, output values should be in [0, 1]."""
    from backend.nodes.shade import Shade

    node = Shade()
    field = make_field(shape=(64, 64))
    result, = node.process(field, azimuth=315.0, elevation=45.0, blend=1.0)
    assert result.data.min() >= 0.0 - 1e-12
    assert result.data.max() <= 1.0 + 1e-12


def test_flat_surface():
    """A flat (constant) surface should produce uniform-ish shading output."""
    from backend.nodes.shade import Shade

    node = Shade()
    data = np.ones((64, 64), dtype=np.float64) * 5.0
    field = make_field(data=data)
    result, = node.process(field, azimuth=315.0, elevation=45.0, blend=1.0)
    # Flat surface -> all surface normals point straight up -> uniform shading
    assert np.std(result.data) < 1e-10
