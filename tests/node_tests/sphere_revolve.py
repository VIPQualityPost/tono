import numpy as np
from tests.node_tests._shared import make_field


def test_sphere_revolve_basic():
    from backend.nodes.sphere_revolve import SphereRevolve

    node = SphereRevolve()
    y, x = np.mgrid[:64, :64] / 64.0
    data = 10.0 * (x ** 2 + y ** 2)
    field = make_field(data=data)

    leveled, bg = node.process(field, radius=30)
    assert leveled.data.shape == data.shape
    assert bg.data.shape == data.shape
    assert np.allclose(leveled.data + bg.data, data)


def test_sphere_revolve_flat():
    from backend.nodes.sphere_revolve import SphereRevolve

    node = SphereRevolve()
    data = np.ones((32, 32)) * 3.0
    field = make_field(data=data)

    leveled, bg = node.process(field, radius=20)
    assert leveled.data.std() < 1e-10
    assert np.allclose(leveled.data + bg.data, data)


def test_sphere_revolve_outputs_two_fields():
    from backend.nodes.sphere_revolve import SphereRevolve

    node = SphereRevolve()
    data = np.random.default_rng(7).standard_normal((32, 32))
    field = make_field(data=data)

    result = node.process(field, radius=15)
    assert len(result) == 2
    leveled, bg = result
    assert np.allclose(leveled.data + bg.data, data)
