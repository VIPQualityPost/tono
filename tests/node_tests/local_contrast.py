import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_local_contrast_shape_preserved():
    from backend.nodes.local_contrast import LocalContrast

    node = LocalContrast()
    field = make_field(shape=(48, 64))
    result, = node.process(field, kernel_size=10, weight=0.5)
    assert result.data.shape == (48, 64)


def test_local_contrast_weight_zero_unchanged():
    """weight=0 blends 100% original → result equals input."""
    from backend.nodes.local_contrast import LocalContrast

    node = LocalContrast()
    data = np.random.default_rng(0).standard_normal((32, 32))
    field = make_field(data=data)
    result, = node.process(field, kernel_size=5, weight=0.0)
    assert np.allclose(result.data, data)


def test_local_contrast_uniform_field_unchanged():
    """A flat field has nothing to enhance; it should be returned as-is."""
    from backend.nodes.local_contrast import LocalContrast

    node = LocalContrast()
    field = make_field(data=np.full((32, 32), 2.0))
    result, = node.process(field, kernel_size=5, weight=1.0)
    assert np.allclose(result.data, 2.0)


def test_local_contrast_increases_dynamic_range():
    """Weight=1 full enhancement should not compress global range beyond input."""
    from backend.nodes.local_contrast import LocalContrast

    rng = np.random.default_rng(1)
    data = rng.standard_normal((64, 64))
    field = make_field(data=data)
    node = LocalContrast()
    result, = node.process(field, kernel_size=8, weight=1.0)
    # Global min/max should be preserved (by construction of the algorithm)
    assert np.isclose(result.data.min(), data.min(), atol=1e-6)
    assert np.isclose(result.data.max(), data.max(), atol=1e-6)


def test_local_contrast_preserves_metadata():
    from backend.nodes.local_contrast import LocalContrast

    node = LocalContrast()
    field = make_field()
    result, = node.process(field, kernel_size=10, weight=0.5)
    assert result.xreal == field.xreal
    assert result.si_unit_z == field.si_unit_z


def test_local_contrast_weight_clipped():
    """Values outside [0,1] should be clipped without error."""
    from backend.nodes.local_contrast import LocalContrast

    node = LocalContrast()
    field = make_field()
    result, = node.process(field, kernel_size=5, weight=2.0)
    assert result.data.shape == field.data.shape
