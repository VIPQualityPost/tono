import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import mask_to_bool


def test_outlier_mask_detects_spikes():
    from backend.nodes.outlier_mask import OutlierMask

    node = OutlierMask()
    data = np.zeros((64, 64))
    data[30, 30] = 100.0  # extreme spike
    field = make_field(data=data)
    mask, = node.process(field, 3.0, "both")
    binary = mask_to_bool(mask)
    assert binary[30, 30]  # spike should be flagged


def test_outlier_mask_clean_field():
    from backend.nodes.outlier_mask import OutlierMask

    node = OutlierMask()
    # Uniform field has no outliers
    field = make_field(data=np.ones((32, 32)) * 5.0)
    mask, = node.process(field, 3.0, "both")
    assert mask_to_bool(mask).sum() == 0


def test_outlier_mask_high_only():
    from backend.nodes.outlier_mask import OutlierMask

    node = OutlierMask()
    data = np.zeros((64, 64))
    data[10, 10] = 100.0   # high spike
    data[50, 50] = -100.0  # low spike
    field = make_field(data=data)
    mask, = node.process(field, 3.0, "high")
    binary = mask_to_bool(mask)
    assert binary[10, 10]
    assert not binary[50, 50]


def test_outlier_mask_low_only():
    from backend.nodes.outlier_mask import OutlierMask

    node = OutlierMask()
    data = np.zeros((64, 64))
    data[10, 10] = 100.0
    data[50, 50] = -100.0
    field = make_field(data=data)
    mask, = node.process(field, 3.0, "low")
    binary = mask_to_bool(mask)
    assert not binary[10, 10]
    assert binary[50, 50]


def test_outlier_mask_preview():
    """Outlier Mask previews the mask overlaid on its field."""
    from backend.nodes.outlier_mask import OutlierMask
    from backend.execution_context import active_node, execution_callbacks

    node = OutlierMask()
    data = np.zeros((32, 32))
    data[10, 10] = 100.0
    field = make_field(data=data)

    previews = []
    with execution_callbacks(preview=lambda nid, d: previews.append(d)), active_node("test"):
        mask, = node.process(field, 3.0, "high")
    assert mask.dtype == np.uint8
    assert len(previews) == 1
    assert previews[0].startswith("data:image/png;base64,")
