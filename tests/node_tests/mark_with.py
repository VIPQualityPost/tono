import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _mask_bool(mask):
    """Convert an IMAGE mask (uint8 0/255) back to a boolean array."""
    return np.asarray(mask) > 127


def test_mark_with_output_arity():
    """The node returns exactly one output matching its OUTPUTS tuple."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    a = make_field(data=np.zeros((16, 16)))
    b = make_field(data=np.zeros((16, 16)))
    result = node.process(a, b, operation="==", invert_mask=False)
    assert len(result) == len(MarkWith.OUTPUTS) == 1
    mask = result[0]
    assert mask.dtype == np.uint8
    assert mask.shape == (16, 16)
    assert set(np.unique(mask)) <= {0, 255}


def test_mark_with_relational_conditions():
    """Relational ops mark exactly the pixels where the comparison holds."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    rng = np.random.default_rng(3)
    a = make_field(data=rng.standard_normal((32, 32)))
    b = make_field(data=rng.standard_normal((32, 32)))

    for op in ("==", "!=", "<", "<=", ">", ">="):
        expected = {
            "==": a.data == b.data,
            "!=": a.data != b.data,
            "<": a.data < b.data,
            "<=": a.data <= b.data,
            ">": a.data > b.data,
            ">=": a.data >= b.data,
        }[op]
        (mask,) = node.process(a, b, operation=op, invert_mask=False)
        np.testing.assert_array_equal(_mask_bool(mask), expected, err_msg=f"op {op}")


def test_mark_with_arithmetic_nonzero():
    """Arithmetic ops mark pixels where the combined value is non-zero."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    a = make_field(data=np.arange(24, dtype=np.float64).reshape(4, 6))
    b = make_field(data=np.ones((4, 6)))

    (mask,) = node.process(a, b, operation="-", invert_mask=False)
    expected = (a.data - b.data) != 0
    np.testing.assert_array_equal(_mask_bool(mask), expected)

    # a and b equal everywhere -> difference is all zero -> nothing marked
    (mask,) = node.process(a, a, operation="-", invert_mask=False)
    assert not _mask_bool(mask).any()


def test_mark_with_invert_mask():
    """invert_mask flips the condition result."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    a = make_field(data=np.zeros((8, 8)))
    b = make_field(data=np.ones((8, 8)))

    (plain,) = node.process(a, b, operation="<", invert_mask=False)
    (inverted,) = node.process(a, b, operation="<", invert_mask=True)
    np.testing.assert_array_equal(_mask_bool(inverted), ~_mask_bool(plain))
    assert _mask_bool(plain).all()
    assert not _mask_bool(inverted).any()


def test_mark_with_divide_semantics():
    """Division by zero is IEEE (inf/NaN), which is non-zero and thus marked."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    a = make_field(data=np.array([[0.0, 5.0], [0.0, 0.0]]))
    b = make_field(data=np.array([[0.0, 2.0], [3.0, 0.0]]))
    (mask,) = node.process(a, b, operation="/", invert_mask=False)
    # 0/0 = NaN, 5/2 = 2.5, 0/3 = 0 (not marked), 0/0 = NaN -> all but (1,0)
    expected = np.array([[True, True], [False, True]])
    np.testing.assert_array_equal(_mask_bool(mask), expected)


def test_mark_with_shape_mismatch_raises():
    """Incompatible field resolutions raise a ValueError."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    a = make_field(data=np.zeros((8, 8)))
    b = make_field(data=np.zeros((16, 16)))
    with pytest.raises(ValueError):
        node.process(a, b, operation="==", invert_mask=False)


def test_mark_with_unknown_operation_raises():
    """An unrecognised operation is rejected."""
    from backend.nodes.mark_with import MarkWith

    node = MarkWith()
    a = make_field(data=np.zeros((8, 8)))
    b = make_field(data=np.zeros((8, 8)))
    with pytest.raises(ValueError):
        node.process(a, b, operation="bogus", invert_mask=False)
