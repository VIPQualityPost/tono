import numpy as np


def test_mask_invert():
    from backend.nodes.mask_invert import MaskInvert
    node = MaskInvert()

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:20, 10:20] = 255

    inverted, = node.process(mask)
    assert inverted.dtype == np.uint8
    assert np.all(inverted[10:20, 10:20] == 0)
    assert np.all(inverted[0:10, 0:10] == 255)

    double, = node.process(inverted)
    assert np.array_equal(double, mask)


def test_mask_invert_with_field():
    from backend.nodes.mask_invert import MaskInvert
    from backend.execution_context import active_node, execution_callbacks
    from tests.node_tests._shared import make_field

    node = MaskInvert()
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:24, 8:24] = 255
    field = make_field(data=np.ones((32, 32)))

    previews = []
    with execution_callbacks(preview=lambda nid, d: previews.append(d)), active_node("test"):
        inverted, = node.process(mask, field=field)
    assert inverted.dtype == np.uint8
    assert len(previews) == 1
    assert previews[0].startswith("data:image/png;base64,")
