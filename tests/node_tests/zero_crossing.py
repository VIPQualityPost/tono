import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_binary():
    from backend.nodes.zero_crossing import ZeroCrossing

    node = ZeroCrossing()
    field = make_field()
    (edges,) = node.process(field, sigma=2.0, threshold=0.0)
    unique = set(np.unique(edges.data))
    assert unique <= {0.0, 1.0}, f"Expected only 0.0/1.0, got {unique}"


def test_detects_step_edge():
    from backend.nodes.zero_crossing import ZeroCrossing

    node = ZeroCrossing()
    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)
    (edges,) = node.process(field, sigma=2.0, threshold=0.0)

    # Edge energy should concentrate near column 32
    col_energy = edges.data.sum(axis=0)
    peak_col = np.argmax(col_energy)
    assert abs(peak_col - 32) <= 3, f"Peak at col {peak_col}, expected ~32"


def test_shape_preserved():
    from backend.nodes.zero_crossing import ZeroCrossing

    node = ZeroCrossing()
    field = make_field(shape=(48, 96))
    (edges,) = node.process(field, sigma=1.5, threshold=0.1)
    assert edges.data.shape == (48, 96)
