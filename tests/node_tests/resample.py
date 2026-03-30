import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_resample_upsample():
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field(shape=(32, 32))
    result, = node.process(field, width=64, height=64, interpolation="linear")

    assert result.data.shape == (64, 64)
    assert np.isclose(result.xreal, field.xreal)
    assert np.isclose(result.yreal, field.yreal)
    # dx should halve since physical size is same but twice the pixels
    assert np.isclose(result.dx, field.dx / 2, rtol=1e-9)


def test_resample_downsample():
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field(shape=(64, 64))
    result, = node.process(field, width=32, height=32, interpolation="linear")

    assert result.data.shape == (32, 32)
    assert np.isclose(result.xreal, field.xreal)


def test_resample_non_square():
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field(shape=(32, 64))
    result, = node.process(field, width=128, height=64, interpolation="nearest")

    assert result.data.shape == (64, 128)


def test_resample_interpolation_modes():
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field(shape=(32, 32))

    for interp in ("linear", "cubic", "nearest"):
        result, = node.process(field, width=64, height=64, interpolation=interp)
        assert result.data.shape == (64, 64)


def test_resample_constant_field():
    """Resampling a constant field should remain constant regardless of interpolation."""
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field(data=np.full((16, 16), 3.14))

    for interp in ("linear", "cubic", "nearest"):
        result, = node.process(field, width=32, height=32, interpolation=interp)
        assert np.allclose(result.data, 3.14, atol=1e-6)


def test_resample_metadata_preserved():
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field()
    result, = node.process(field, width=64, height=64, interpolation="linear")

    assert result.si_unit_xy == field.si_unit_xy
    assert result.si_unit_z == field.si_unit_z
    assert np.isclose(result.xreal, field.xreal)


def test_resample_unknown_interpolation():
    from backend.nodes.resample import Resample

    node = Resample()
    field = make_field()

    with pytest.raises(ValueError, match="interpolation"):
        node.process(field, width=64, height=64, interpolation="lanczos")
