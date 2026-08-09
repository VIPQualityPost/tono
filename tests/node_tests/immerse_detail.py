import numpy as np
import pytest
from backend.data_types import RecordTable
from tests.node_tests._shared import make_field


def test_output_shape_matches_overview():
    from backend.nodes.immerse_detail import ImmerseDetail

    node = ImmerseDetail()
    overview = make_field(shape=(64, 64))
    # Detail must have matching pixel size (smaller physical area)
    detail = make_field(shape=(16, 16), xreal=0.25e-6, yreal=0.25e-6)
    combined, placement = node.process(overview, detail, blend="replace")
    assert combined.data.shape == overview.data.shape
    # Placement table locates the detail within the overview
    assert isinstance(placement, RecordTable)
    assert len(placement) == 5
    quantities = {row["quantity"] for row in placement}
    assert {"Placement X (px)", "Placement Y (px)", "Placement X", "Placement Y", "Match score"} <= quantities
    for row in placement:
        assert set(row) == {"quantity", "value", "unit"}


def test_detail_larger_returns_overview():
    from backend.nodes.immerse_detail import ImmerseDetail

    node = ImmerseDetail()
    overview = make_field(shape=(32, 32))
    # Detail larger than overview after resampling
    detail = make_field(shape=(64, 64))
    combined, placement = node.process(overview, detail, blend="replace")
    # Should return the overview unchanged
    assert np.array_equal(combined.data, overview.data)
    # No placement found: detail stays at origin
    assert isinstance(placement, RecordTable)
    assert len(placement) == 5
    by_quantity = {row["quantity"]: row["value"] for row in placement}
    assert by_quantity["Placement X (px)"] == 0.0
    assert by_quantity["Placement Y (px)"] == 0.0
    assert by_quantity["Match score"] == -np.inf


def test_replace_mode():
    from backend.nodes.immerse_detail import ImmerseDetail

    node = ImmerseDetail()
    overview_data = np.zeros((64, 64))
    detail_data = np.ones((16, 16)) * 5.0
    overview = make_field(data=overview_data)
    # Match pixel size so detail stays 16x16 (smaller than 64x64)
    detail = make_field(data=detail_data, xreal=0.25e-6, yreal=0.25e-6)
    combined, placement = node.process(overview, detail, blend="replace")
    # After immersion, some pixels should now equal 5.0
    assert np.any(combined.data == 5.0), "Detail should modify some pixels in replace mode"
    # But not all pixels changed
    assert combined.data.shape == (64, 64)
    # Detail is placed somewhere within the overview bounds
    assert isinstance(placement, RecordTable)
    assert len(placement) == 5
    by_quantity = {row["quantity"]: row["value"] for row in placement}
    assert 0 <= by_quantity["Placement X (px)"] <= 64 - 16
    assert 0 <= by_quantity["Placement Y (px)"] <= 64 - 16
    assert by_quantity["Match score"] > -np.inf
