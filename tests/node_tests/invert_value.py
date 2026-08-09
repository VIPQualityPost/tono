import numpy as np
from backend.data_types import DataField


def test_outputs_arity():
    from backend.nodes.invert_value import InvertValue

    assert len(InvertValue.OUTPUTS) == 1
    assert InvertValue.OUTPUTS[0][0] == "DATA_FIELD"

    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    field = DataField(data=data, si_unit_xy="m", si_unit_z="V")
    result = InvertValue().process(field, mode="z")
    assert isinstance(result, tuple) and len(result) == 1


def test_z_mode_reflects_about_mean():
    """gwy_data_field_invert(zflipped): data = 2*mean - data (mean preserved)."""
    from backend.nodes.invert_value import InvertValue

    data = np.array([[1.0, 2.0], [3.0, 10.0]])
    field = DataField(data=data)
    out, = InvertValue().process(field, mode="z")

    avg = data.mean()
    assert np.allclose(out.data, 2.0 * avg - data)
    assert np.isclose(out.data.mean(), avg)


def test_z_mode_zero_mean_is_negation():
    from backend.nodes.invert_value import InvertValue

    data = np.array([[-1.0, 0.0], [1.0, 2.0]]) - 0.5  # mean 0
    field = DataField(data=data)
    out, = InvertValue().process(field, mode="z")
    assert np.allclose(out.data, -data)


def test_x_mode_mirrors_left_right():
    from backend.nodes.invert_value import InvertValue

    data = np.arange(1, 10, dtype=np.float64).reshape(3, 3)
    out, = InvertValue().process(DataField(data=data), mode="x")
    assert np.array_equal(out.data, np.fliplr(data))


def test_y_mode_mirrors_top_bottom():
    from backend.nodes.invert_value import InvertValue

    data = np.arange(1, 10, dtype=np.float64).reshape(3, 3)
    out, = InvertValue().process(DataField(data=data), mode="y")
    assert np.array_equal(out.data, np.flipud(data))


def test_metadata_and_units_preserved():
    from backend.node_registry import get_node_info
    from backend.nodes.invert_value import InvertValue

    assert get_node_info("InvertValue")["category"] == "Level & Correct"

    field = DataField(
        data=np.array([[1.0, 2.0], [3.0, 4.0]]),
        xreal=2.5e-6, yreal=3.0e-6, xoff=1.0e-7, yoff=-2.0e-7,
        si_unit_xy="m", si_unit_z="V",
    )
    out, = InvertValue().process(field, mode="z")
    assert out.xreal == field.xreal
    assert out.yreal == field.yreal
    assert out.xoff == field.xoff
    assert out.yoff == field.yoff
    assert out.si_unit_xy == "m"
    assert out.si_unit_z == "V"


def test_invalid_mode_raises():
    from backend.nodes.invert_value import InvertValue

    field = DataField(data=np.array([[1.0, 2.0], [3.0, 4.0]]))
    try:
        InvertValue().process(field, mode="diagonal")
        raise AssertionError("Expected invalid mode to raise ValueError")
    except ValueError:
        pass
