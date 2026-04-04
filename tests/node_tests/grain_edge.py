import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import mask_to_bool, bool_to_mask


def test_boundary_detection():
    from backend.nodes.grain_edge import GrainEdge

    node = GrainEdge()
    data = np.zeros((64, 64))
    data[22:42, 22:42] = 1.0
    field = make_field(data=data)

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[22:42, 22:42] = 255

    (edge_mask,) = node.process(field, mask=mask, width=1)
    edge_bool = mask_to_bool(edge_mask)

    # Edge pixels should lie on the grain boundary (outermost ring of the grain)
    assert edge_bool.any(), "Should detect some edge pixels"
    # Boundary pixels: grain pixels with at least one non-grain 4-neighbour
    # Rows 22 and 41 (top/bottom edges), cols 22 and 41 (left/right edges)
    assert edge_bool[22, 30], "Top boundary row should be marked"
    assert edge_bool[41, 30], "Bottom boundary row should be marked"
    assert edge_bool[30, 22], "Left boundary col should be marked"
    assert edge_bool[30, 41], "Right boundary col should be marked"


def test_interior_excluded():
    from backend.nodes.grain_edge import GrainEdge

    node = GrainEdge()
    data = np.zeros((64, 64))
    data[10:50, 10:50] = 1.0
    field = make_field(data=data)

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:50, 10:50] = 255

    (edge_mask,) = node.process(field, mask=mask, width=1)
    edge_bool = mask_to_bool(edge_mask)

    # Deep interior pixel (centre of the 40x40 grain) should NOT be edge
    assert not edge_bool[30, 30], "Interior pixel should not be in edge mask"
    assert not edge_bool[25, 25], "Another interior pixel should not be edge"


def test_width_expands():
    from backend.nodes.grain_edge import GrainEdge

    node = GrainEdge()
    data = np.zeros((64, 64))
    data[15:45, 15:45] = 1.0
    field = make_field(data=data)

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[15:45, 15:45] = 255

    (edge1,) = node.process(field, mask=mask, width=1)
    (edge3,) = node.process(field, mask=mask, width=3)

    count1 = mask_to_bool(edge1).sum()
    count3 = mask_to_bool(edge3).sum()
    assert count3 > count1, f"width=3 ({count3}) should give more edge pixels than width=1 ({count1})"
