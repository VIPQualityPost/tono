import numpy as np
import pytest
from backend.data_types import DataField, RecordTable
from tests.node_tests._shared import make_field


def test_same_image():
    from backend.nodes.mutual_crop import MutualCrop

    node = MutualCrop()
    field = make_field()
    cropped_a, cropped_b, alignment = node.process(field, field)
    assert cropped_a.data.shape == cropped_b.data.shape
    # Identical fields should have zero shift, so crops keep their origin
    assert cropped_a.xoff == 0.0 and cropped_a.yoff == 0.0
    assert cropped_b.xoff == 0.0 and cropped_b.yoff == 0.0
    assert isinstance(alignment, RecordTable)
    assert len(alignment) == 4
    quantities = {row["quantity"] for row in alignment}
    assert {"Shift X (px)", "Shift Y (px)", "Shift X", "Shift Y"} <= quantities
    for row in alignment:
        assert set(row) == {"quantity", "value", "unit"}
    assert alignment[0]["value"] == 0.0  # Shift X (px)
    assert alignment[1]["value"] == 0.0  # Shift Y (px)


def test_output_shapes_match():
    from backend.nodes.mutual_crop import MutualCrop

    node = MutualCrop()
    rng = np.random.default_rng(10)
    field_a = make_field(data=rng.standard_normal((48, 64)))
    field_b = make_field(data=rng.standard_normal((64, 48)))
    cropped_a, cropped_b, alignment = node.process(field_a, field_b)
    assert cropped_a.data.shape == cropped_b.data.shape, (
        f"Shapes should match: {cropped_a.data.shape} vs {cropped_b.data.shape}"
    )
    # Crops keep their physical position: offsets within each own frame are >= 0
    assert cropped_a.xoff >= 0.0 and cropped_a.yoff >= 0.0
    assert cropped_b.xoff >= 0.0 and cropped_b.yoff >= 0.0
    assert isinstance(cropped_a, DataField) and isinstance(cropped_b, DataField)
    assert isinstance(alignment, RecordTable)
    assert len(alignment) == 4
    quantities = {row["quantity"] for row in alignment}
    assert {"Shift X (px)", "Shift Y (px)", "Shift X", "Shift Y"} <= quantities
    for row in alignment:
        assert set(row) == {"quantity", "value", "unit"}


def test_identical_fields():
    from backend.nodes.mutual_crop import MutualCrop

    node = MutualCrop()
    data = np.random.default_rng(99).standard_normal((32, 32))
    field_a = make_field(data=data.copy())
    field_b = make_field(data=data.copy())
    cropped_a, cropped_b, alignment = node.process(field_a, field_b)
    # Identical fields should be fully overlapping, so cropped output ~ original
    assert cropped_a.data.shape == (32, 32)
    assert np.allclose(cropped_a.data, data)
    # Zero shift for identical inputs: crops are the full frame
    assert cropped_a.xoff == 0.0 and cropped_a.yoff == 0.0
    assert cropped_b.xoff == 0.0 and cropped_b.yoff == 0.0
    assert len(alignment) == 4
    assert alignment[0]["value"] == 0.0  # Shift X (px)
    assert alignment[1]["value"] == 0.0  # Shift Y (px)
    assert alignment[2]["unit"] == field_a.si_unit_xy
