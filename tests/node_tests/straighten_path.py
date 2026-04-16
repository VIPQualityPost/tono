import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_basic_extraction():
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))
    result, profile = node.process(field, points_x="0.25, 0.5, 0.75",
                                   points_y="0.5, 0.3, 0.5",
                                   thickness=1, n_samples=256)
    assert result.data.shape[1] == 256, f"Output width should be n_samples=256, got {result.data.shape[1]}"
    assert profile.data.shape == (256,)


def test_thickness():
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))
    result, profile = node.process(field, points_x="0.2, 0.8",
                                   points_y="0.5, 0.5",
                                   thickness=5, n_samples=100)
    assert result.data.shape[0] == 5, f"Output height should be thickness=5, got {result.data.shape[0]}"
    # Profile is the 1-pixel-wide centerline regardless of thickness.
    assert profile.data.shape == (100,)
    # For a horizontal line, the centerline equals the middle row of the strip.
    assert np.allclose(profile.data, result.data[2])


def test_single_point_returns_input():
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))
    result, profile = node.process(field, points_x="0.5",
                                   points_y="0.5",
                                   thickness=1, n_samples=100)
    # With only 1 point, node returns the original field unchanged + empty profile.
    assert np.array_equal(result.data, field.data)
    assert profile.data.shape == (0,)


def test_emits_overlay_with_points_and_thickness():
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))

    overlays = []
    with execution_callbacks(overlay=lambda nid, d: overlays.append(d)), active_node("test"):
        node.process(field, points_x="0.25, 0.5, 0.75",
                     points_y="0.5, 0.3, 0.5",
                     thickness=4, n_samples=128)

    assert len(overlays) == 1
    ov = overlays[0]
    assert ov["kind"] == "straighten_path"
    assert ov["section_title"] == "Path"
    assert ov["image"].startswith("data:image/png;base64,")
    assert ov["thickness"] == 4
    assert ov["xres"] == 64 and ov["yres"] == 64
    assert [p["x"] for p in ov["points"]] == [0.25, 0.5, 0.75]
    assert [p["y"] for p in ov["points"]] == [0.5, 0.3, 0.5]
