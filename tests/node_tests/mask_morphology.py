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
