import numpy as np
from tests.node_tests._shared import make_field


def test_grain_distance_transform():
    from backend.nodes.grain_distance_transform import GrainDistanceTransform

    node = GrainDistanceTransform()
    field = make_field(data=np.zeros((7, 7), dtype=np.float64), xreal=7.0, yreal=7.0)
    mask = np.zeros((7, 7), dtype=np.uint8)
    mask[2:5, 2:5] = 255

    interior, = node.process(field, mask, distance_type="euclidean", output_type="interior", from_border=True)
    assert interior.data.shape == field.data.shape
    assert interior.si_unit_z == field.si_unit_xy
    assert np.isclose(interior.data[3, 3], 2.0)
    assert np.isclose(interior.data[2, 2], 1.0)
    assert np.isclose(interior.data[0, 0], 0.0)

    exterior, = node.process(field, mask, distance_type="cityblock", output_type="exterior", from_border=True)
    assert np.isclose(exterior.data[1, 1], 2.0)
    assert np.isclose(exterior.data[2, 1], 1.0)
    assert np.isclose(exterior.data[3, 3], 0.0)

    signed, = node.process(field, mask, distance_type="chess", output_type="signed", from_border=True)
    assert signed.data[3, 3] > 0.0
    assert signed.data[0, 0] < 0.0

    edge_field = make_field(data=np.zeros((5, 5), dtype=np.float64), xreal=5.0, yreal=5.0)
    edge_mask = np.zeros((5, 5), dtype=np.uint8)
    edge_mask[:, :2] = 255
    from_edge, = node.process(edge_field, edge_mask, distance_type="euclidean", output_type="interior", from_border=True)
    not_from_edge, = node.process(edge_field, edge_mask, distance_type="euclidean", output_type="interior", from_border=False)
    assert not_from_edge.data[2, 0] > from_edge.data[2, 0]
