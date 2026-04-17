import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_identity():
    """All offsets zero should return output approximately equal to input."""
    from backend.nodes.perspective_correction import PerspectiveCorrection

    node = PerspectiveCorrection()
    field = make_field(shape=(64, 64))
    result, = node.process(
        field,
        top_left_x=0.0, top_left_y=0.0,
        top_right_x=0.0, top_right_y=0.0,
        bottom_left_x=0.0, bottom_left_y=0.0,
        bottom_right_x=0.0, bottom_right_y=0.0,
    )
    assert result.data.shape == field.data.shape
    assert np.allclose(result.data, field.data, atol=1e-10)


def test_nonzero_offset():
    """Non-zero offsets should change the data while preserving shape."""
    from backend.nodes.perspective_correction import PerspectiveCorrection

    node = PerspectiveCorrection()
    field = make_field(shape=(64, 64))
    result, = node.process(
        field,
        top_left_x=0.05, top_left_y=0.05,
        top_right_x=-0.05, top_right_y=0.05,
        bottom_left_x=0.05, bottom_left_y=-0.05,
        bottom_right_x=-0.05, bottom_right_y=-0.05,
    )
    assert result.data.shape == field.data.shape
    assert not np.allclose(result.data, field.data)


def test_output_shape():
    """Output shape must match input shape."""
    from backend.nodes.perspective_correction import PerspectiveCorrection

    node = PerspectiveCorrection()
    field = make_field(shape=(48, 96))
    result, = node.process(
        field,
        top_left_x=0.1, top_left_y=0.0,
        top_right_x=0.0, top_right_y=0.0,
        bottom_left_x=0.0, bottom_left_y=0.0,
        bottom_right_x=0.0, bottom_right_y=0.0,
    )
    assert result.data.shape == (48, 96)


def test_emits_perspective_overlay():
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.perspective_correction import PerspectiveCorrection

    node = PerspectiveCorrection()
    field = make_field(shape=(64, 64))

    overlays = []
    with execution_callbacks(overlay=lambda nid, d: overlays.append(d)), active_node("test"):
        node.process(
            field,
            top_left_x=0.05, top_left_y=0.05,
            top_right_x=-0.05, top_right_y=0.05,
            bottom_left_x=0.05, bottom_left_y=-0.05,
            bottom_right_x=-0.05, bottom_right_y=-0.05,
        )

    assert len(overlays) == 1
    ov = overlays[0]
    assert ov["kind"] == "perspective"
    assert ov["section_title"] == "Perspective"
    assert ov["image"].startswith("data:image/png;base64,")
    assert ov["corrected_image"].startswith("data:image/png;base64,")
    assert len(ov["corners"]) == 4
    assert ov["corners"][0] == {"x": 0.05, "y": 0.05}
    assert ov["corners"][3] == {"x": -0.05, "y": -0.05}


def test_coord_input_overrides_floats():
    from backend.nodes.perspective_correction import PerspectiveCorrection

    node = PerspectiveCorrection()
    field = make_field(shape=(64, 64))

    result_floats, = node.process(
        field,
        top_left_x=0.1, top_left_y=0.1,
        top_right_x=0.0, top_right_y=0.0,
        bottom_left_x=0.0, bottom_left_y=0.0,
        bottom_right_x=0.0, bottom_right_y=0.0,
    )

    result_coord, = node.process(
        field,
        top_left_x=0.0, top_left_y=0.0,
        top_right_x=0.0, top_right_y=0.0,
        bottom_left_x=0.0, bottom_left_y=0.0,
        bottom_right_x=0.0, bottom_right_y=0.0,
        top_left=(0.1, 0.1),
    )

    assert np.allclose(result_floats.data, result_coord.data)
