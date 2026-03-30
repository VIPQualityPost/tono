import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_field_arithmetic_basic():
    from backend.nodes.field_arithmetic import FieldArithmetic

    node = FieldArithmetic()
    a = make_field(data=np.array([[1.0, 2.0], [3.0, 4.0]]))
    b = make_field(data=np.array([[1.0, 1.0], [1.0, 1.0]]))

    result, = node.process(a, b, "add")
    assert np.allclose(result.data, [[2.0, 3.0], [4.0, 5.0]])

    result, = node.process(a, b, "subtract")
    assert np.allclose(result.data, [[0.0, 1.0], [2.0, 3.0]])

    result, = node.process(a, b, "multiply")
    assert np.allclose(result.data, [[1.0, 2.0], [3.0, 4.0]])

    result, = node.process(a, b, "divide")
    assert np.allclose(result.data, [[1.0, 2.0], [3.0, 4.0]])

    result, = node.process(a, b, "min")
    assert np.allclose(result.data, [[1.0, 1.0], [1.0, 1.0]])

    result, = node.process(a, b, "max")
    assert np.allclose(result.data, [[1.0, 2.0], [3.0, 4.0]])


def test_field_arithmetic_hypot():
    from backend.nodes.field_arithmetic import FieldArithmetic

    node = FieldArithmetic()
    a = make_field(data=np.array([[3.0, 0.0], [0.0, 5.0]]))
    b = make_field(data=np.array([[4.0, 5.0], [3.0, 12.0]]))

    result, = node.process(a, b, "hypot")
    assert np.allclose(result.data, [[5.0, 5.0], [3.0, 13.0]])


def test_field_arithmetic_metadata_inherited():
    from backend.nodes.field_arithmetic import FieldArithmetic

    node = FieldArithmetic()
    a = make_field(data=np.ones((4, 4)))
    b = make_field(data=np.ones((4, 4)))

    result, = node.process(a, b, "add")
    assert result.xreal == a.xreal
    assert result.si_unit_xy == a.si_unit_xy
    assert result.si_unit_z == a.si_unit_z


def test_field_arithmetic_shape_mismatch():
    from backend.nodes.field_arithmetic import FieldArithmetic

    node = FieldArithmetic()
    a = make_field(data=np.ones((4, 4)))
    b = make_field(data=np.ones((3, 3)))

    with pytest.raises(ValueError, match="resolution"):
        node.process(a, b, "add")


def test_field_arithmetic_unknown_operation():
    from backend.nodes.field_arithmetic import FieldArithmetic

    node = FieldArithmetic()
    a = make_field(data=np.ones((4, 4)))
    b = make_field(data=np.ones((4, 4)))

    with pytest.raises(ValueError):
        node.process(a, b, "power")
