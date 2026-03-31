import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_cross_correlate_same_field_peak_at_center():
    """Correlating a field with itself in 'same' mode peaks at the centre."""
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(0)
    data = rng.standard_normal((32, 32))
    field = make_field(data=data)
    node = CrossCorrelate()
    result, = node.process(field, field, mode="same", normalize=True)

    peak_y, peak_x = np.unravel_index(np.argmax(result.data), result.data.shape)
    cy, cx = result.data.shape[0] // 2, result.data.shape[1] // 2
    # Peak should be within a few pixels of centre
    assert abs(peak_y - cy) <= 2
    assert abs(peak_x - cx) <= 2


def test_cross_correlate_same_mode_shape_equals_a():
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(1)
    a = make_field(data=rng.standard_normal((32, 48)))
    b = make_field(data=rng.standard_normal((32, 48)))
    node = CrossCorrelate()
    result, = node.process(a, b, mode="same", normalize=True)
    assert result.data.shape == a.data.shape


def test_cross_correlate_full_mode_shape():
    """Full mode output shape should be Na+Nb-1 × Ma+Mb-1."""
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(2)
    a = make_field(data=rng.standard_normal((20, 30)))
    b = make_field(data=rng.standard_normal((20, 30)))
    node = CrossCorrelate()
    result, = node.process(a, b, mode="full", normalize=True)
    assert result.data.shape == (20 + 20 - 1, 30 + 30 - 1)


def test_cross_correlate_normalized_peak_is_one():
    """Self-correlation normalised should give peak = 1."""
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(3)
    data = rng.standard_normal((32, 32))
    field = make_field(data=data)
    node = CrossCorrelate()
    result, = node.process(field, field, mode="same", normalize=True)
    assert result.data.max() == pytest.approx(1.0, abs=1e-6)


def test_cross_correlate_unnormalized_runs():
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(4)
    data = rng.standard_normal((16, 16))
    field = make_field(data=data)
    node = CrossCorrelate()
    result, = node.process(field, field, mode="same", normalize=False)
    assert result.data.shape == (16, 16)


def test_cross_correlate_valid_mode():
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(5)
    a = make_field(data=rng.standard_normal((16, 16)))
    b = make_field(data=rng.standard_normal((8, 8)))
    node = CrossCorrelate()
    result, = node.process(a, b, mode="valid", normalize=True)
    # Valid mode output: (16-8+1, 16-8+1) = (9, 9)
    assert result.data.shape == (9, 9)


def test_cross_correlate_preserves_metadata_same_mode():
    from backend.nodes.cross_correlate import CrossCorrelate

    rng = np.random.default_rng(6)
    field = make_field(data=rng.standard_normal((16, 16)))
    node = CrossCorrelate()
    result, = node.process(field, field, mode="same", normalize=True)
    assert result.xreal == field.xreal
    assert result.yreal == field.yreal
