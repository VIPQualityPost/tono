import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.mark_disconnected import MarkDisconnected

    node = MarkDisconnected()
    field = make_field(shape=(64, 64))
    mask, = node.process(field, defect_type="both", radius=5, threshold=0.1)
    assert mask.shape == (64, 64)


def test_flat_surface_no_defects():
    from backend.nodes.mark_disconnected import MarkDisconnected

    node = MarkDisconnected()
    data = np.ones((64, 64)) * 5.0
    field = make_field(data=data)
    mask, = node.process(field, defect_type="both", radius=5, threshold=0.1)
    assert np.count_nonzero(mask) == 0


def test_spike_detected():
    from backend.nodes.mark_disconnected import MarkDisconnected

    node = MarkDisconnected()
    data = np.ones((64, 64), dtype=np.float64)
    mean_val = data.mean()
    data[32, 32] = mean_val * 100  # large spike
    field = make_field(data=data)
    mask, = node.process(field, defect_type="positive", radius=3, threshold=0.05)
    assert mask[32, 32] == 255


def test_output_is_uint8():
    from backend.nodes.mark_disconnected import MarkDisconnected

    node = MarkDisconnected()
    field = make_field(shape=(32, 32))
    mask, = node.process(field, defect_type="negative", radius=5, threshold=0.1)
    assert mask.dtype == np.uint8
