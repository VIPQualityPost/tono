import numpy as np
from backend.data_types import DataField
from tests.node_tests._shared import make_field


def test_outputs_arity():
    from backend.nodes.square_samples import SquareSamples

    assert len(SquareSamples.OUTPUTS) == 1
    assert SquareSamples.OUTPUTS[0][0] == "DATA_FIELD"

    field = make_field(data=np.zeros((32, 64)), shape=None)
    result = SquareSamples().process(field, interpolation="cubic")
    assert isinstance(result, tuple) and len(result) == 1


def test_y_axis_gains_pixels_to_match_x():
    """Gwyddion square_samples: qx > qy -> yres becomes round(yreal*qx), dx == dy."""
    from backend.nodes.square_samples import SquareSamples

    # 32 rows x 64 cols over a square physical area: qx = 2*qy
    data = np.tile(np.linspace(0.0, 1.0, 64), (32, 1))
    field = DataField(data=data, xreal=1.0e-6, yreal=1.0e-6, si_unit_xy="m", si_unit_z="m")

    out, = SquareSamples().process(field, interpolation="linear")

    assert out.data.shape == (64, 64)
    assert out.xreal == field.xreal and out.yreal == field.yreal
    # dx == dy after resampling
    assert np.isclose(out.xreal / out.data.shape[1], out.yreal / out.data.shape[0])
    # The x-linear ramp survives: each column stays (nearly) constant
    col_spread = np.abs(out.data - out.data[:1, :]).max()
    assert col_spread < 1e-9


def test_x_axis_gains_pixels_to_match_y():
    """Gwyddion square_samples: qx < qy -> xres becomes round(xreal*qy)."""
    from backend.nodes.square_samples import SquareSamples

    # 64 rows x 32 cols over a square physical area: qx = qy/2
    data = np.tile(np.linspace(0.0, 1.0, 64)[:, None], (1, 32))
    field = DataField(data=data, xreal=1.0e-6, yreal=1.0e-6, si_unit_xy="m", si_unit_z="m")

    out, = SquareSamples().process(field, interpolation="linear")

    assert out.data.shape == (64, 64)
    assert np.isclose(out.xreal / out.data.shape[1], out.yreal / out.data.shape[0])
    # The y-linear ramp survives: each row stays (nearly) constant
    row_spread = np.abs(out.data - out.data[:, :1]).max()
    assert row_spread < 1e-9


def test_equal_ratios_return_unchanged():
    """When qx == qy the field is duplicated without resampling."""
    from backend.nodes.square_samples import SquareSamples

    data = np.random.default_rng(0).standard_normal((32, 32))
    field = make_field(data=data)

    out, = SquareSamples().process(field, interpolation="cubic")

    assert out.data.shape == (32, 32)
    assert np.array_equal(out.data, data)
    assert out.data is not field.data  # it is a fresh copy


def test_interpolations_all_run():
    from backend.nodes.square_samples import SquareSamples

    data = np.tile(np.linspace(0.0, 1.0, 64), (32, 1))
    field = DataField(data=data, xreal=1.0e-6, yreal=1.0e-6)
    for interp in ("linear", "cubic", "nearest"):
        out, = SquareSamples().process(field, interpolation=interp)
        assert out.data.shape == (64, 64)
        assert np.isnan(out.data).sum() == 0


def test_metadata_preserved():
    from backend.node_registry import get_node_info
    from backend.nodes.square_samples import SquareSamples

    assert get_node_info("SquareSamples")["category"] == "Geometry"

    data = np.tile(np.linspace(0.0, 1.0, 64), (32, 1))
    field = DataField(
        data=data, xreal=2.0e-6, yreal=1.0e-6, xoff=3.0e-7, yoff=-4.0e-7,
        si_unit_xy="nm", si_unit_z="m",
    )
    out, = SquareSamples().process(field, interpolation="cubic")
    assert out.xreal == field.xreal and out.yreal == field.yreal
    assert out.xoff == field.xoff and out.yoff == field.yoff
    assert out.si_unit_xy == "nm" and out.si_unit_z == "m"


def test_unknown_interpolation_raises():
    from backend.nodes.square_samples import SquareSamples

    field = make_field()
    try:
        SquareSamples().process(field, interpolation="sinc")
        raise AssertionError("Expected unknown interpolation to raise ValueError")
    except ValueError:
        pass
