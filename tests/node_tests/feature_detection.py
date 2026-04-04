import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_canny_edge_detection():
    from backend.nodes.feature_detection import FeatureDetection

    node = FeatureDetection()
    # Create a field with a sharp edge
    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)
    result, records = node.process(field, "canny", 1.0)
    assert result.data.shape == (64, 64)
    # Should detect some edge pixels
    assert result.data.sum() > 0
    assert isinstance(records, list)


def test_harris_corner_detection():
    from backend.nodes.feature_detection import FeatureDetection

    node = FeatureDetection()
    # Create a field with a sharp corner (L-shape)
    data = np.zeros((64, 64))
    data[16:48, 16:48] = 1.0
    field = make_field(data=data)
    result, records = node.process(field, "harris", 1.0)
    assert result.data.shape == (64, 64)
    assert isinstance(records, list)


def test_canny_flat_field():
    from backend.nodes.feature_detection import FeatureDetection

    node = FeatureDetection()
    field = make_field(data=np.ones((32, 32)))
    result, records = node.process(field, "canny", 1.0)
    # Flat field should have no edges
    assert result.data.sum() == 0


def test_unknown_method():
    from backend.nodes.feature_detection import FeatureDetection

    node = FeatureDetection()
    field = make_field(shape=(32, 32))
    with pytest.raises(ValueError):
        node.process(field, "unknown", 1.0)
