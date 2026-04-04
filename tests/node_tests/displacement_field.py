import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.displacement_field import DisplacementField

    node = DisplacementField()
    field = make_field(shape=(48, 64))
    result, = node.process(field, "gaussian_1d", sigma=5.0, tau=20.0, density=0.02, seed=42)
    assert result.data.shape == (48, 64)


def test_zero_sigma_unchanged():
    from backend.nodes.displacement_field import DisplacementField

    node = DisplacementField()
    field = make_field(shape=(32, 32))
    result, = node.process(field, "gaussian_1d", sigma=0.1, tau=20.0, density=0.02, seed=42)
    np.testing.assert_allclose(result.data, field.data, atol=0.5)


def test_gaussian_2d_modifies():
    from backend.nodes.displacement_field import DisplacementField

    node = DisplacementField()
    field = make_field(shape=(32, 32))
    result, = node.process(field, "gaussian_2d", sigma=10.0, tau=20.0, density=0.02, seed=42)
    # With sigma=10 the output should differ from the input
    assert not np.allclose(result.data, field.data, atol=1e-3)


def test_all_methods_finite():
    from backend.nodes.displacement_field import DisplacementField

    node = DisplacementField()
    field = make_field(shape=(32, 32))
    for method in ("gaussian_1d", "gaussian_2d", "tear"):
        result, = node.process(field, method, sigma=5.0, tau=20.0, density=0.02, seed=42)
        assert np.all(np.isfinite(result.data)), f"{method} produced non-finite values"
