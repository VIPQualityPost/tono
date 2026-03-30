import numpy as np


def test_mask_morphology():
    from backend.nodes.mask_morphology import MaskMorphology
    node = MaskMorphology()

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[28:36, 28:36] = 255
    orig_count = np.count_nonzero(mask)

    dilated, = node.process(mask, operation="dilate", radius=1, shape="square")
    assert dilated.dtype == np.uint8
    assert np.count_nonzero(dilated) > orig_count

    eroded, = node.process(mask, operation="erode", radius=1, shape="square")
    assert np.count_nonzero(eroded) < orig_count

    opened, = node.process(mask, operation="open", radius=1, shape="square")
    assert np.count_nonzero(opened) <= orig_count

    mask_hole = mask.copy()
    mask_hole[32, 32] = 0
    assert np.count_nonzero(mask_hole) == orig_count - 1
    closed, = node.process(mask_hole, operation="close", radius=1, shape="square")
    assert closed[32, 32] == 255

    dilated_disk, = node.process(mask, operation="dilate", radius=2, shape="disk")
    assert np.count_nonzero(dilated_disk) > orig_count


def test_mask_morphology_with_field():
    from backend.nodes.mask_morphology import MaskMorphology
    from backend.execution_context import active_node, execution_callbacks
    from tests.node_tests._shared import make_field

    node = MaskMorphology()
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[10:22, 10:22] = 255
    field = make_field(data=np.ones((32, 32)))

    previews = []
    with execution_callbacks(preview=lambda nid, d: previews.append(d)), active_node("test"):
        dilated, = node.process(mask, operation="dilate", radius=1, shape="square", field=field)
    assert dilated.dtype == np.uint8
    assert len(previews) == 1


def test_mask_morphology_unknown_operation():
    from backend.nodes.mask_morphology import MaskMorphology
    node = MaskMorphology()
    mask = np.zeros((32, 32), dtype=np.uint8)
    try:
        node.process(mask, operation="invalid_op", radius=1, shape="square")
        assert False, "Expected ValueError"
    except ValueError:
        pass
