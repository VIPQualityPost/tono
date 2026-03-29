import numpy as np
from tests.node_tests._shared import make_field


def test_edge_detect():
    from backend.nodes.edge_detect import EdgeDetect
    node = EdgeDetect()

    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)

    for method in ["sobel", "prewitt", "laplacian", "log"]:
        result, = node.process(field, method=method, sigma=1.0)
        assert result.data.shape == field.data.shape
        col_energy = np.abs(result.data).sum(axis=0)
        peak_col = np.argmax(col_energy)
        assert abs(peak_col - 32) <= 2, f"{method}: peak at col {peak_col}, expected ~32"
