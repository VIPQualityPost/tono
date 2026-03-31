import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_kuwahara_shape_preserved():
    from backend.nodes.filter_kuwahara import KuwaharaFilter

    node = KuwaharaFilter()
    field = make_field(shape=(48, 64))
    result, = node.process(field, iterations=1)
    assert result.data.shape == (48, 64)


def test_kuwahara_flat_field_unchanged():
    """A constant field should pass through the Kuwahara filter unchanged."""
    from backend.nodes.filter_kuwahara import KuwaharaFilter

    node = KuwaharaFilter()
    field = make_field(data=np.full((32, 32), 7.5))
    result, = node.process(field, iterations=1)
    assert np.allclose(result.data, 7.5)


def test_kuwahara_reduces_noise():
    """Applying the filter to a noisy field should reduce standard deviation."""
    from backend.nodes.filter_kuwahara import KuwaharaFilter

    rng = np.random.default_rng(0)
    noisy = rng.standard_normal((64, 64))
    node = KuwaharaFilter()
    field = make_field(data=noisy)
    result, = node.process(field, iterations=1)
    assert result.data.std() < noisy.std()


def test_kuwahara_preserves_step_edge():
    """The Kuwahara filter should preserve a sharp step edge better than a blur."""
    from backend.nodes.filter_kuwahara import KuwaharaFilter

    # Left half = 0, right half = 1
    data = np.zeros((32, 64))
    data[:, 32:] = 1.0
    node = KuwaharaFilter()
    field = make_field(data=data)
    result, = node.process(field, iterations=1)

    # The edge column should have a large jump (edge preserved)
    col_before = result.data[:, 30].mean()
    col_after = result.data[:, 34].mean()
    assert col_after - col_before > 0.5


def test_kuwahara_multiple_iterations():
    """Running multiple iterations should further reduce noise."""
    from backend.nodes.filter_kuwahara import KuwaharaFilter

    rng = np.random.default_rng(1)
    noisy = rng.standard_normal((32, 32))
    node = KuwaharaFilter()
    field = make_field(data=noisy)
    result1, = node.process(field, iterations=1)
    result3, = node.process(field, iterations=3)
    assert result3.data.std() <= result1.data.std()


def test_kuwahara_preserves_metadata():
    from backend.nodes.filter_kuwahara import KuwaharaFilter

    node = KuwaharaFilter()
    field = make_field()
    result, = node.process(field, iterations=1)
    assert result.xreal == field.xreal
    assert result.yreal == field.yreal
    assert result.si_unit_z == field.si_unit_z
