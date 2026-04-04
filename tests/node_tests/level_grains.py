import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import bool_to_mask


def test_level_grains_equalizes():
    from backend.nodes.level_grains import LevelGrains

    node = LevelGrains()
    data = np.zeros((32, 32))
    # Two grains at different heights
    data[5:10, 5:10] = 3.0
    data[20:25, 20:25] = 7.0
    mask = np.zeros((32, 32), dtype=bool)
    mask[5:10, 5:10] = True
    mask[20:25, 20:25] = True
    field = make_field(data=data)
    result, = node.process(field, bool_to_mask(mask), "mean")
    # After leveling, both grains should have similar mean heights
    g1 = result.data[5:10, 5:10].mean()
    g2 = result.data[20:25, 20:25].mean()
    assert abs(g1 - g2) < 0.1


def test_level_grains_no_grains():
    from backend.nodes.level_grains import LevelGrains

    node = LevelGrains()
    field = make_field(shape=(32, 32))
    mask = bool_to_mask(np.zeros((32, 32), dtype=bool))
    result, = node.process(field, mask, "mean")
    assert np.allclose(result.data, field.data)


def test_level_grains_median_reference():
    from backend.nodes.level_grains import LevelGrains

    node = LevelGrains()
    data = np.zeros((32, 32))
    data[5:15, 5:15] = 2.0
    mask = np.zeros((32, 32), dtype=bool)
    mask[5:15, 5:15] = True
    field = make_field(data=data)
    result, = node.process(field, bool_to_mask(mask), "median")
    assert result.data.shape == (32, 32)
