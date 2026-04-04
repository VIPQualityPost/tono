import numpy as np
from tests.node_tests._shared import make_field


def test_keep_mode_unchanged():
    from backend.nodes.calibration import Calibration
    node = Calibration()
    field = make_field(data=np.array([[1.0, 2.0], [3.0, 4.0]]))

    result, = node.process(
        field,
        xy_mode="keep", z_mode="keep",
        xreal_new=1e-6, yreal_new=1e-6, xy_scale=1.0,
        z_min=0.0, z_max=1e-9, z_scale=1.0, z_offset=0.0,
        xy_unit="", z_unit="",
    )

    assert np.array_equal(result.data, field.data)
    assert result.xreal == field.xreal
    assert result.yreal == field.yreal
    assert result.si_unit_xy == field.si_unit_xy
    assert result.si_unit_z == field.si_unit_z


def test_set_size():
    from backend.nodes.calibration import Calibration
    node = Calibration()
    field = make_field(data=np.array([[1.0, 2.0], [3.0, 4.0]]))

    result, = node.process(
        field,
        xy_mode="set_size", z_mode="keep",
        xreal_new=5e-6, yreal_new=3e-6, xy_scale=1.0,
        z_min=0.0, z_max=1e-9, z_scale=1.0, z_offset=0.0,
        xy_unit="", z_unit="",
    )

    assert result.xreal == 5e-6
    assert result.yreal == 3e-6
    assert np.array_equal(result.data, field.data)


def test_z_scale():
    from backend.nodes.calibration import Calibration
    node = Calibration()
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    field = make_field(data=data.copy())

    result, = node.process(
        field,
        xy_mode="keep", z_mode="scale",
        xreal_new=1e-6, yreal_new=1e-6, xy_scale=1.0,
        z_min=0.0, z_max=1e-9, z_scale=2.0, z_offset=0.0,
        xy_unit="", z_unit="",
    )

    np.testing.assert_allclose(result.data, data * 2.0)


def test_z_set_range():
    from backend.nodes.calibration import Calibration
    node = Calibration()
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    field = make_field(data=data.copy())

    result, = node.process(
        field,
        xy_mode="keep", z_mode="set_range",
        xreal_new=1e-6, yreal_new=1e-6, xy_scale=1.0,
        z_min=0.0, z_max=1.0, z_scale=1.0, z_offset=0.0,
        xy_unit="", z_unit="",
    )

    assert float(result.data.min()) == 0.0
    assert float(result.data.max()) == 1.0
    # Check that intermediate values are linearly mapped
    np.testing.assert_allclose(result.data, (data - 1.0) / 3.0)
