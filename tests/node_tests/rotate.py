import numpy as np
from backend.data_types import DataField


def test_rotate_field():
    from backend.nodes.rotate import RotateField
    node = RotateField()

    data = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float64)
    field = DataField(data=data, xreal=6.0, yreal=4.0, xoff=10.0, yoff=20.0, si_unit_xy="nm", si_unit_z="nm")

    rotated_90, = node.process(field, angle=90.0, interpolation="nearest", expand_canvas=True)
    assert np.array_equal(rotated_90.data, np.rot90(data))
    assert rotated_90.data.shape == (3, 2)
    assert rotated_90.xreal == 4.0
    assert rotated_90.yreal == 6.0
    assert rotated_90.xoff == 11.0
    assert rotated_90.yoff == 19.0
    assert rotated_90.si_unit_xy == field.si_unit_xy
    assert rotated_90.si_unit_z == field.si_unit_z
    assert rotated_90.overlays == []

    rotated_180, = node.process(field, angle=180.0, interpolation="nearest", expand_canvas=False)
    assert np.array_equal(rotated_180.data, np.rot90(data, 2))
    assert rotated_180.data.shape == data.shape
    assert rotated_180.xreal == field.xreal
    assert rotated_180.yreal == field.yreal
    assert rotated_180.xoff == field.xoff
    assert rotated_180.yoff == field.yoff

    rotated_45, = node.process(field, angle=45.0, interpolation="bilinear", expand_canvas=True)
    expected_xreal = abs(field.xreal * np.cos(np.deg2rad(45.0))) + abs(field.yreal * np.sin(np.deg2rad(45.0)))
    expected_yreal = abs(field.xreal * np.sin(np.deg2rad(45.0))) + abs(field.yreal * np.cos(np.deg2rad(45.0)))
    assert rotated_45.data.shape[0] > field.data.shape[0]
    assert rotated_45.data.shape[1] > field.data.shape[1]
    assert np.isclose(rotated_45.xreal, expected_xreal)
    assert np.isclose(rotated_45.yreal, expected_yreal)
    assert np.isclose(rotated_45.xoff + rotated_45.xreal / 2.0, field.xoff + field.xreal / 2.0)
    assert np.isclose(rotated_45.yoff + rotated_45.yreal / 2.0, field.yoff + field.yreal / 2.0)


def test_rotate_field_overlay_warning():
    from backend.nodes.rotate import RotateField

    from backend.execution_context import execution_callbacks, active_node
    node = RotateField()
    warnings = []

    field = DataField(
        data=np.arange(16, dtype=np.float64).reshape(4, 4),
        overlays=[{"kind": "markup", "shapes": [{"kind": "line", "x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9, "width": 2, "color": "#ffffff"}]}],
    )

    with execution_callbacks(warning=lambda nid, msg: warnings.append(msg)), active_node("test"):
        rotated, = node.process(field, angle=30.0, interpolation="bilinear", expand_canvas=True)
        assert rotated.overlays == []
        assert len(warnings) == 1
        assert "clears annotation/markup overlays" in warnings[0]


def test_rotate_unknown_interpolation():
    from backend.nodes.rotate import RotateField
    node = RotateField()
    field = DataField(data=np.arange(9, dtype=np.float64).reshape(3, 3))
    try:
        node.process(field, angle=0.0, interpolation="invalid", expand_canvas=False)
        assert False, "Expected ValueError"
    except ValueError:
        pass
