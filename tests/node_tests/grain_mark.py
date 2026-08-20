import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import mask_to_bool


def test_grain_mark_height():
    from backend.nodes.grain_mark import GrainMark

    node = GrainMark()
    data = np.zeros((64, 64))
    data[20:40, 20:40] = 1.0  # raised region
    field = make_field(data=data)
    mask, = node.process(field, "height", 0.5, 1.0, 10, False)
    binary = mask_to_bool(mask)
    assert binary[30, 30]  # center of raised region should be marked
    assert not binary[0, 0]  # corner should not be marked


def test_grain_mark_slope():
    from backend.nodes.grain_mark import GrainMark

    node = GrainMark()
    field = make_field(shape=(64, 64))
    mask, = node.process(field, "slope", 0.3, 1.0, 5, False)
    assert mask.shape == (64, 64)
    assert mask.dtype == np.uint8


def test_grain_mark_inverted():
    from backend.nodes.grain_mark import GrainMark

    node = GrainMark()
    data = np.zeros((32, 32))
    data[10:20, 10:20] = 1.0
    field = make_field(data=data)
    mask_normal, = node.process(field, "height", 0.5, 1.0, 1, False)
    mask_inv, = node.process(field, "height", 0.5, 1.0, 1, True)
    # Inverted should be complement (approximately)
    n1 = mask_to_bool(mask_normal).sum()
    n2 = mask_to_bool(mask_inv).sum()
    assert n1 + n2 > 0


def test_grain_mark_min_size():
    from backend.nodes.grain_mark import GrainMark

    node = GrainMark()
    data = np.zeros((64, 64))
    data[30, 30] = 1.0  # single pixel
    data[10:20, 10:20] = 1.0  # larger region
    field = make_field(data=data)
    mask, = node.process(field, "height", 0.5, 1.0, 50, False)
    binary = mask_to_bool(mask)
    # Single pixel should be filtered out
    assert not binary[30, 30]


def test_grain_mark_preview():
    """Grain Mark previews the mask overlaid on its field."""
    from backend.nodes.grain_mark import GrainMark
    from backend.execution_context import active_node, execution_callbacks

    node = GrainMark()
    data = np.zeros((32, 32))
    data[10:20, 10:20] = 1.0
    field = make_field(data=data)

    previews = []
    with execution_callbacks(preview=lambda nid, d: previews.append(d)), active_node("test"):
        mask, = node.process(field, "height", 0.5, 1.0, 1, False)
    assert mask.dtype == np.uint8
    assert len(previews) == 1
    assert previews[0].startswith("data:image/png;base64,")
