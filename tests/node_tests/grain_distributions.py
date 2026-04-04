import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import bool_to_mask


def test_grain_distributions_area():
    from backend.nodes.grain_distributions import GrainDistributions

    node = GrainDistributions()
    data = np.zeros((64, 64))
    data[10:20, 10:20] = 1.0
    data[40:50, 40:50] = 1.0
    mask = np.zeros((64, 64), dtype=bool)
    mask[10:20, 10:20] = True
    mask[40:50, 40:50] = True
    field = make_field(data=data)
    dist, = node.process(field, bool_to_mask(mask), "area", 10, 5)
    assert hasattr(dist, 'data')
    assert len(dist.data) == 10  # n_bins


def test_grain_distributions_height():
    from backend.nodes.grain_distributions import GrainDistributions

    node = GrainDistributions()
    data = np.zeros((32, 32))
    data[5:15, 5:15] = 2.0
    data[20:28, 20:28] = 5.0
    mask = np.zeros((32, 32), dtype=bool)
    mask[5:15, 5:15] = True
    mask[20:28, 20:28] = True
    field = make_field(data=data)
    dist, = node.process(field, bool_to_mask(mask), "mean_height", 10, 5)
    assert len(dist.data) == 10


def test_grain_distributions_no_grains():
    from backend.nodes.grain_distributions import GrainDistributions

    node = GrainDistributions()
    field = make_field(shape=(32, 32))
    mask = bool_to_mask(np.zeros((32, 32), dtype=bool))
    dist, = node.process(field, mask, "area", 10, 5)
    assert hasattr(dist, 'data')
