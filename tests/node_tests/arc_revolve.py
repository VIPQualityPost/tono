import numpy as np
from tests.node_tests._shared import make_field


def test_arc_revolve_horizontal():
    from backend.nodes.arc_revolve import ArcRevolve

    node = ArcRevolve()
    rng = np.random.default_rng(42)
    x = np.linspace(0, 1, 64)
    bow = 10.0 * x ** 2
    data = bow[None, :] + rng.standard_normal((64, 64)) * 0.01
    field = make_field(data=data)

    leveled, bg = node.process(field, radius=40, direction="horizontal")
    assert leveled.data.shape == field.data.shape
    assert bg.data.shape == field.data.shape
    assert np.allclose(leveled.data + bg.data, data)


def test_arc_revolve_vertical():
    from backend.nodes.arc_revolve import ArcRevolve

    node = ArcRevolve()
    y = np.linspace(0, 1, 64)
    data = (5.0 * y ** 2)[:, None] * np.ones((1, 64))
    field = make_field(data=data)

    leveled, bg = node.process(field, radius=40, direction="vertical")
    assert np.allclose(leveled.data + bg.data, data)


def test_arc_revolve_both():
    from backend.nodes.arc_revolve import ArcRevolve

    node = ArcRevolve()
    y, x = np.mgrid[:32, :32] / 32.0
    data = 5.0 * x ** 2 + 3.0 * y ** 2
    field = make_field(data=data)

    leveled, bg = node.process(field, radius=30, direction="both")
    assert leveled.data.shape == data.shape
    assert bg.data.shape == data.shape


def test_arc_revolve_flat_passthrough():
    from backend.nodes.arc_revolve import ArcRevolve

    node = ArcRevolve()
    data = np.ones((32, 32)) * 5.0
    field = make_field(data=data)

    leveled, bg = node.process(field, radius=20, direction="horizontal")
    assert leveled.data.std() < 1e-10
    assert np.allclose(leveled.data + bg.data, data)
