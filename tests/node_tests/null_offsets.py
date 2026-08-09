import numpy as np
from backend.data_types import DataField
from tests.node_tests._shared import make_field


def test_outputs_arity():
    from backend.nodes.null_offsets import NullOffsets

    assert len(NullOffsets.OUTPUTS) == 1
    assert NullOffsets.OUTPUTS[0][0] == "DATA_FIELD"

    result = NullOffsets().process(make_field())
    assert isinstance(result, tuple) and len(result) == 1


def test_sets_offsets_to_zero():
    """gwy_data_field_set_xoffset/set_yoffset(0.0): offsets nulled, data untouched."""
    from backend.nodes.null_offsets import NullOffsets

    data = np.random.default_rng(1).standard_normal((16, 24))
    field = DataField(
        data=data, xreal=2.0e-6, yreal=1.5e-6, xoff=3.0e-7, yoff=-2.0e-7,
        si_unit_xy="nm", si_unit_z="m",
    )

    out, = NullOffsets().process(field)

    assert out.xoff == 0.0
    assert out.yoff == 0.0
    assert np.array_equal(out.data, data)
    assert out.xreal == field.xreal and out.yreal == field.yreal
    assert out.si_unit_xy == "nm" and out.si_unit_z == "m"


def test_already_zero_offsets_still_returns_valid_field():
    from backend.nodes.null_offsets import NullOffsets

    field = make_field()
    out, = NullOffsets().process(field)
    assert out.xoff == 0.0 and out.yoff == 0.0
    assert out.data.shape == field.data.shape


def test_category():
    from backend.node_registry import get_node_info

    assert get_node_info("NullOffsets")["category"] == "Level & Correct"
