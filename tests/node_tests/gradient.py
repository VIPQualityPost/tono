import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_gradient_flat_field():
    from backend.nodes.gradient import Gradient

    node = Gradient()
    field = make_field(data=np.zeros((16, 16)))

    for component in ("magnitude", "x", "y"):
        result, = node.process(field, component)
        assert np.allclose(result.data, 0.0)
        assert result.data.shape == field.data.shape


def test_gradient_x_ramp():
    """Linear ramp in x should give uniform x-gradient and zero y-gradient."""
    from backend.nodes.gradient import Gradient

    node = Gradient()
    data = np.tile(np.linspace(0.0, 1.0, 32), (32, 1))
    field = make_field(data=data)

    gx, = node.process(field, "x")
    gy, = node.process(field, "y")

    # Interior pixels should have nearly identical x-gradient values
    interior_gx = gx.data[1:-1, 1:-1]
    assert np.all(interior_gx > 0)
    assert np.std(interior_gx) < np.mean(interior_gx) * 0.01

    # y-gradient should be zero everywhere in the interior
    assert np.allclose(gy.data[1:-1, 1:-1], 0.0, atol=1e-10)


def test_gradient_magnitude_non_negative():
    from backend.nodes.gradient import Gradient

    node = Gradient()
    field = make_field()

    result, = node.process(field, "magnitude")
    assert np.all(result.data >= 0.0)


def test_gradient_azimuth_range():
    from backend.nodes.gradient import Gradient

    node = Gradient()
    field = make_field()

    result, = node.process(field, "azimuth")
    assert np.all(result.data >= -np.pi - 1e-10)
    assert np.all(result.data <= np.pi + 1e-10)
    assert result.si_unit_z == "rad"


def test_gradient_units():
    from backend.nodes.gradient import Gradient

    node = Gradient()
    field = make_field()  # si_unit_z="m", si_unit_xy="m"

    result, = node.process(field, "magnitude")
    assert result.si_unit_z == "m/m"

    result, = node.process(field, "x")
    assert result.si_unit_z == "m/m"


def test_gradient_shape_preserved():
    from backend.nodes.gradient import Gradient

    node = Gradient()
    field = make_field(shape=(48, 64))

    for component in ("magnitude", "x", "y", "azimuth"):
        result, = node.process(field, component)
        assert result.data.shape == (48, 64)


def test_gradient_unknown_component():
    from backend.nodes.gradient import Gradient

    node = Gradient()
    field = make_field()

    with pytest.raises(ValueError):
        node.process(field, "diagonal")
