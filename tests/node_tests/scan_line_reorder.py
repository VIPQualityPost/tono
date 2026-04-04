import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_reverse_odd_fixes_meander():
    from backend.nodes.scan_line_reorder import ScanLineReorder

    node = ScanLineReorder()
    data = np.arange(32 * 32, dtype=np.float64).reshape(32, 32)
    # Simulate meander: reverse odd rows
    meander = data.copy()
    meander[1::2, :] = meander[1::2, ::-1]
    field = make_field(data=meander)
    result, = node.process(field, "reverse_odd")
    # Should restore original order
    assert np.allclose(result.data, data)


def test_reverse_even():
    from backend.nodes.scan_line_reorder import ScanLineReorder

    node = ScanLineReorder()
    field = make_field(shape=(32, 32))
    result, = node.process(field, "reverse_even")
    assert result.data.shape == (32, 32)


def test_deinterlace_odd():
    from backend.nodes.scan_line_reorder import ScanLineReorder

    node = ScanLineReorder()
    field = make_field(shape=(32, 32))
    result, = node.process(field, "deinterlace_odd")
    assert result.data.shape[1] == 32


def test_flip_vertical():
    from backend.nodes.scan_line_reorder import ScanLineReorder

    node = ScanLineReorder()
    data = np.arange(16 * 16, dtype=np.float64).reshape(16, 16)
    field = make_field(data=data)
    result, = node.process(field, "flip_vertical")
    assert np.array_equal(result.data, data[::-1, :])


def test_unknown_operation():
    from backend.nodes.scan_line_reorder import ScanLineReorder

    node = ScanLineReorder()
    field = make_field(shape=(16, 16))
    with pytest.raises(ValueError):
        node.process(field, "unknown")
