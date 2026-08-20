import numpy as np


def test_mask_operations():
    from backend.nodes.mask_operations import MaskOperations
    node = MaskOperations()

    a = np.zeros((64, 64), dtype=np.uint8)
    a[10:30, 10:30] = 255
    b = np.zeros((64, 64), dtype=np.uint8)
    b[20:40, 20:40] = 255

    result_and, = node.process(a, b, operation="and")
    assert np.all(result_and[20:30, 20:30] == 255)
    assert result_and[15, 15] == 0
    assert result_and[35, 35] == 0

    result_or, = node.process(a, b, operation="or")
    assert result_or[15, 15] == 255
    assert result_or[35, 35] == 255
    assert result_or[25, 25] == 255
    assert result_or[5, 5] == 0

    result_xor, = node.process(a, b, operation="xor")
    assert result_xor[15, 15] == 255
    assert result_xor[35, 35] == 255
    assert result_xor[25, 25] == 0

    result_sub, = node.process(a, b, operation="a_minus_b")
    assert result_sub[15, 15] == 255
    assert result_sub[25, 25] == 0
    assert result_sub[35, 35] == 0

    result_nand, = node.process(a, b, operation="nand")
    assert result_nand[15, 15] == 255
    assert result_nand[35, 35] == 255
    assert result_nand[25, 25] == 0
    assert result_nand[5, 5] == 255

    result_xnor, = node.process(a, b, operation="xnor")
    assert result_xnor[25, 25] == 255
    assert result_xnor[5, 5] == 255
    assert result_xnor[15, 15] == 0
    assert result_xnor[35, 35] == 0


def test_mask_operations_unknown_operation():
    from backend.nodes.mask_operations import MaskOperations
    node = MaskOperations()
    a = np.zeros((16, 16), dtype=np.uint8)
    b = np.zeros((16, 16), dtype=np.uint8)
    try:
        node.process(a, b, operation="invalid_op")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_mask_operations_preview():
    """Mask Operations always previews its result mask."""
    from backend.nodes.mask_operations import MaskOperations
    from backend.execution_context import active_node, execution_callbacks

    a = np.zeros((16, 16), dtype=np.uint8)
    a[4:12, 4:12] = 255
    b = np.zeros((16, 16), dtype=np.uint8)
    b[8:16, 8:16] = 255

    previews = []
    with execution_callbacks(preview=lambda nid, d: previews.append(d)), active_node("test"):
        out, = MaskOperations().process(a, b, operation="or")
    assert out[8:12, 8:12].all()
    assert len(previews) == 1
    assert previews[0].startswith("data:image/png;base64,")
