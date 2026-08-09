import numpy as np
from backend.data_types import DataField


def test_outputs_arity():
    from backend.nodes.limit_range import LimitRange

    assert len(LimitRange.OUTPUTS) == 1
    assert LimitRange.OUTPUTS[0][0] == "DATA_FIELD"

    field = DataField(data=np.array([[0.0, 1.0], [2.0, 3.0]]))
    result = LimitRange().process(field, low=0.0, high=1.0, mode="clip")
    assert isinstance(result, tuple) and len(result) == 1


def test_clip_clamps_values():
    """Values outside [min(low,high), max(low,high)] are clamped."""
    from backend.nodes.limit_range import LimitRange

    data = np.array([[-2.0, -1.0], [0.5, 3.0]])
    out, = LimitRange().process(DataField(data=data), low=-1.0, high=1.0, mode="clip")
    assert np.array_equal(out.data, np.array([[-1.0, -1.0], [0.5, 1.0]]))


def test_clip_swaps_low_high():
    """Low and high are interchangeable."""
    from backend.nodes.limit_range import LimitRange

    data = np.array([[-2.0, 0.0], [2.0, 5.0]])
    node = LimitRange()
    out_a, = node.process(DataField(data=data), low=-1.0, high=1.0, mode="clip")
    out_b, = node.process(DataField(data=data), low=1.0, high=-1.0, mode="clip")
    assert np.array_equal(out_a.data, out_b.data)
    assert np.array_equal(out_a.data, np.array([[-1.0, 0.0], [1.0, 1.0]]))


def test_scale_maps_range_to_unit_interval():
    """Scale mode: clamp to [low, high] then map low -> 0, high -> 1."""
    from backend.nodes.limit_range import LimitRange

    data = np.array([[0.0, 1.0], [2.0, 3.0]])
    out, = LimitRange().process(DataField(data=data), low=1.0, high=3.0, mode="scale")
    assert np.allclose(out.data, np.array([[0.0, 0.0], [0.5, 1.0]]))


def test_clip_preserves_metadata():
    from backend.node_registry import get_node_info
    from backend.nodes.limit_range import LimitRange

    assert get_node_info("LimitRange")["category"] == "Level & Correct"

    field = DataField(
        data=np.array([[-2.0, 3.0]]),
        xreal=1.0e-6, yreal=2.0e-6, xoff=1.0e-8, yoff=5.0e-8,
        si_unit_xy="nm", si_unit_z="V",
    )
    out, = LimitRange().process(field, low=-1.0, high=1.0, mode="clip")
    assert out.xreal == field.xreal and out.yreal == field.yreal
    assert out.xoff == field.xoff and out.yoff == field.yoff
    assert out.si_unit_xy == "nm" and out.si_unit_z == "V"
    assert np.allclose(out.data, np.array([[-1.0, 1.0]]))


def test_scale_degenerate_range_raises():
    from backend.nodes.limit_range import LimitRange

    field = DataField(data=np.array([[0.0, 1.0]]))
    try:
        LimitRange().process(field, low=2.0, high=2.0, mode="scale")
        raise AssertionError("Expected degenerate scale range to raise ValueError")
    except ValueError:
        pass


def test_unknown_mode_raises():
    from backend.nodes.limit_range import LimitRange

    field = DataField(data=np.array([[0.0, 1.0]]))
    try:
        LimitRange().process(field, low=0.0, high=1.0, mode="squash")
        raise AssertionError("Expected unknown mode to raise ValueError")
    except ValueError:
        pass
