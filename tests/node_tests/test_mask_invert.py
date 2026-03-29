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
