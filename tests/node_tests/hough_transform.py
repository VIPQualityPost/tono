import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_hough_lines_basic():
    from backend.nodes.hough_transform import HoughTransform

    node = HoughTransform()
    # Create a field with a horizontal line
    data = np.zeros((64, 64))
    data[32, :] = 1.0
    field = make_field(data=data)
    accum, records = node.process(field, "lines", 3, 1.0, 10, 30)
    assert accum.data.ndim == 2
    assert isinstance(records, list)


def test_hough_circles_basic():
    from backend.nodes.hough_transform import HoughTransform

    node = HoughTransform()
    # Create a field with a circle
    data = np.zeros((64, 64))
    yy, xx = np.ogrid[:64, :64]
    r2 = (yy - 32)**2 + (xx - 32)**2
    data[(r2 > 144) & (r2 < 196)] = 1.0  # ring at radius ~13
    field = make_field(data=data)
    accum, records = node.process(field, "circles", 3, 1.0, 8, 20)
    assert accum.data.shape == (64, 64)
    assert isinstance(records, list)


def test_hough_preserves_output_types():
    from backend.nodes.hough_transform import HoughTransform

    node = HoughTransform()
    field = make_field(shape=(32, 32))
    accum, records = node.process(field, "lines", 2, 1.0, 5, 15)
    assert hasattr(accum, 'data')
    assert isinstance(records, list)


def test_hough_unknown_mode():
    from backend.nodes.hough_transform import HoughTransform

    node = HoughTransform()
    field = make_field(shape=(32, 32))
    with pytest.raises(ValueError):
        node.process(field, "unknown", 1, 1.0, 5, 15)
