import numpy as np
from tests.node_tests._shared import make_field


def test_statistics():
    from backend.nodes.statistics import Statistics
    node = Statistics()

    data = np.array([[1, 2], [3, 4]], dtype=np.float64)
    field = make_field(data=data)

    table, = node.process(field)
    stats = {row["quantity"]: row["value"] for row in table}

    assert stats["min"] == 1.0
    assert stats["max"] == 4.0
    assert stats["mean"] == 2.5
    assert stats["median"] == 2.5
    assert stats["range"] == 3.0
    expected_rms = np.sqrt(np.mean((data - 2.5) ** 2))
    assert abs(stats["RMS"] - expected_rms) < 1e-10

    const_field = make_field(data=np.ones((4, 4)) * 5.0)
    table_const, = node.process(const_field)
    const_stats = {row["quantity"]: row["value"] for row in table_const}
    assert const_stats["RMS"] == 0.0
    assert const_stats["skewness"] == 0.0
    assert const_stats["kurtosis"] == 0.0


def test_statistics_with_mask():
    """A mask restricts the stats to pixels where mask != 0."""
    from backend.nodes.statistics import Statistics
    node = Statistics()

    data = np.array([[1, 2], [3, 4]], dtype=np.float64)
    field = make_field(data=data)
    # Mask selects only pixels >= 3 (bottom row).
    mask = np.array([[0, 0], [255, 255]], dtype=np.uint8)

    table, = node.process(field, mask=mask)
    stats = {row["quantity"]: row["value"] for row in table}
    assert stats["min"] == 3.0
    assert stats["max"] == 4.0
    assert stats["mean"] == 3.5


def test_statistics_mask_shape_mismatch():
    from backend.nodes.statistics import Statistics
    node = Statistics()

    field = make_field(data=np.zeros((4, 4)))
    bad_mask = np.zeros((3, 3), dtype=np.uint8)
    try:
        node.process(field, mask=bad_mask)
        raise AssertionError("expected shape mismatch to raise")
    except ValueError:
        pass


def test_statistics_empty_mask():
    from backend.nodes.statistics import Statistics
    node = Statistics()

    field = make_field(data=np.ones((4, 4)))
    empty_mask = np.zeros((4, 4), dtype=np.uint8)
    try:
        node.process(field, mask=empty_mask)
        raise AssertionError("expected empty mask to raise")
    except ValueError:
        pass
