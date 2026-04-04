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
