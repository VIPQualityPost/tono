import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import bool_to_mask


def test_basic_correlation():
    from backend.nodes.grain_cross import GrainCross

    node = GrainCross()

    rng = np.random.default_rng(42)
    data_a = rng.standard_normal((64, 64))
    data_b = rng.standard_normal((64, 64))
    field_a = make_field(data=data_a)
    field_b = make_field(data=data_b)

    # Create mask with two distinct grains
    mask_bool = np.zeros((64, 64), dtype=bool)
    mask_bool[5:20, 5:20] = True
    mask_bool[40:55, 40:55] = True
    mask = bool_to_mask(mask_bool)

    (table,) = node.process(field_a, field_b, mask=mask,
                            property_a="mean_height", property_b="max_height",
                            min_size=10)
    assert len(table) > 0, "Should return entries for detected grains"


def test_pearson_reported():
    from backend.nodes.grain_cross import GrainCross

    node = GrainCross()

    rng = np.random.default_rng(7)
    data_a = rng.standard_normal((64, 64))
    data_b = rng.standard_normal((64, 64))
    field_a = make_field(data=data_a)
    field_b = make_field(data=data_b)

    # Two grains so Pearson can be computed
    mask_bool = np.zeros((64, 64), dtype=bool)
    mask_bool[5:20, 5:20] = True
    mask_bool[40:55, 40:55] = True
    mask = bool_to_mask(mask_bool)

    (table,) = node.process(field_a, field_b, mask=mask,
                            property_a="mean_height", property_b="mean_height",
                            min_size=10)
    quantities = [row["quantity"] for row in table]
    assert "Pearson r" in quantities, f"Expected 'Pearson r' in {quantities}"


def test_min_size_filters():
    from backend.nodes.grain_cross import GrainCross

    node = GrainCross()

    data_a = np.zeros((64, 64))
    data_b = np.zeros((64, 64))
    field_a = make_field(data=data_a)
    field_b = make_field(data=data_b)

    # Small grain (10x10 = 100 pixels)
    mask_bool = np.zeros((64, 64), dtype=bool)
    mask_bool[5:15, 5:15] = True
    mask = bool_to_mask(mask_bool)

    # min_size larger than any grain
    (table,) = node.process(field_a, field_b, mask=mask,
                            property_a="area", property_b="area",
                            min_size=200)
    # No grain entries (only maybe no Pearson either since < 2 grains)
    grain_entries = [r for r in table if r["quantity"].startswith("Grain")]
    assert len(grain_entries) == 0, "No grains should pass with large min_size"
