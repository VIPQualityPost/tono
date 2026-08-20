import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.nodes.helpers import bool_to_mask


def test_grain_summary_basic():
    from backend.nodes.grain_summary import GrainSummary

    node = GrainSummary()
    data = np.zeros((64, 64))
    data[10:20, 10:20] = 1.0
    data[40:55, 40:55] = 2.0
    mask = np.zeros((64, 64), dtype=bool)
    mask[10:20, 10:20] = True
    mask[40:55, 40:55] = True
    field = make_field(data=data)
    records, = node.process(field, bool_to_mask(mask), 5)
    assert isinstance(records, list)
    # Should have grain count
    quantities = [r["quantity"] for r in records]
    assert "Grain count" in quantities
    count_record = [r for r in records if r["quantity"] == "Grain count"][0]
    assert count_record["value"] == 2


def test_grain_summary_no_grains():
    from backend.nodes.grain_summary import GrainSummary

    node = GrainSummary()
    field = make_field(shape=(32, 32))
    mask = bool_to_mask(np.zeros((32, 32), dtype=bool))
    records, = node.process(field, mask, 5)
    assert isinstance(records, list)
    count_record = [r for r in records if r["quantity"] == "Grain count"][0]
    assert count_record["value"] == 0


def test_grain_summary_coverage():
    from backend.nodes.grain_summary import GrainSummary

    node = GrainSummary()
    data = np.ones((32, 32))
    mask = np.ones((32, 32), dtype=bool)  # entire surface is grain
    field = make_field(data=data)
    records, = node.process(field, bool_to_mask(mask), 1)
    quantities = {r["quantity"]: r for r in records}
    assert "Coverage fraction" in quantities
    assert float(quantities["Coverage fraction"]["value"]) > 0.9
