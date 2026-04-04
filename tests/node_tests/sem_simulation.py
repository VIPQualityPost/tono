import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.sem_simulation import SEMSimulation

    node = SEMSimulation()
    field = make_field(shape=(48, 64))

    for method in ("integration", "monte_carlo"):
        result, = node.process(field, method, sigma=3.0, n_samples=20)
        assert result.data.shape == (48, 64)


def test_flat_surface_zero():
    """Flat topography (all zeros) should produce all-zero or near-zero SEM signal."""
    from backend.nodes.sem_simulation import SEMSimulation

    node = SEMSimulation()
    field = make_field(data=np.zeros((32, 32)))

    for method in ("integration", "monte_carlo"):
        result, = node.process(field, method, sigma=3.0, n_samples=20)
        assert np.allclose(result.data, 0.0, atol=1e-10)


def test_integration_method():
    from backend.nodes.sem_simulation import SEMSimulation

    node = SEMSimulation()
    field = make_field()

    result, = node.process(field, "integration", sigma=3.0, n_samples=20)
    assert np.all(np.isfinite(result.data))


def test_monte_carlo_method():
    from backend.nodes.sem_simulation import SEMSimulation

    node = SEMSimulation()
    field = make_field()

    result, = node.process(field, "monte_carlo", sigma=3.0, n_samples=20)
    assert np.all(np.isfinite(result.data))
