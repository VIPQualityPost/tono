import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_basic_extraction():
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))
    (result,) = node.process(field, points_x="0.25, 0.5, 0.75",
                             points_y="0.5, 0.3, 0.5",
                             thickness=1, n_samples=256)
    assert result.data.shape[1] == 256, f"Output width should be n_samples=256, got {result.data.shape[1]}"


def test_thickness():
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))
    (result,) = node.process(field, points_x="0.2, 0.8",
                             points_y="0.5, 0.5",
                             thickness=5, n_samples=100)
    assert result.data.shape[0] == 5, f"Output height should be thickness=5, got {result.data.shape[0]}"


def test_single_point_returns_input():
    from backend.nodes.straighten_path import StraightenPath

    node = StraightenPath()
    field = make_field(shape=(64, 64))
    (result,) = node.process(field, points_x="0.5",
                             points_y="0.5",
                             thickness=1, n_samples=100)
    # With only 1 point, node returns the original field unchanged
    assert np.array_equal(result.data, field.data)
