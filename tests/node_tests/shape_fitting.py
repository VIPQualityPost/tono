import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_fit_sphere_residual():
    from backend.nodes.shape_fitting import ShapeFitting

    node = ShapeFitting()
    # Create a spherical surface
    y, x = np.mgrid[:32, :32]
    data = 100.0 - np.sqrt(np.maximum(500**2 - (x - 16)**2 - (y - 16)**2, 0))
    field = make_field(data=data)
    result, records = node.process(field, "sphere", "residual")
    assert result.data.shape == (32, 32)
    assert isinstance(records, list)


def test_fit_paraboloid():
    from backend.nodes.shape_fitting import ShapeFitting

    node = ShapeFitting()
    field = make_field(shape=(32, 32))
    result, records = node.process(field, "paraboloid", "fitted")
    assert result.data.shape == (32, 32)
    assert isinstance(records, list)


def test_fit_cylinder():
    from backend.nodes.shape_fitting import ShapeFitting

    node = ShapeFitting()
    field = make_field(shape=(32, 32))
    result, records = node.process(field, "cylinder", "residual")
    assert result.data.shape == (32, 32)
    assert isinstance(records, list)


def test_fit_unknown_shape():
    from backend.nodes.shape_fitting import ShapeFitting

    node = ShapeFitting()
    field = make_field(shape=(32, 32))
    with pytest.raises(ValueError):
        node.process(field, "cone", "residual")
