import numpy as np
import pytest
from backend.data_types import RecordTable
from tests.node_tests._shared import make_field


def test_stitch_right_no_overlap():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(data=np.ones((32, 32)))
    b = make_field(data=np.ones((32, 32)) * 2)
    result, alignment = node.process(a, b, "right", "none")
    assert result.data.shape[0] == 32
    assert result.data.shape[1] >= 32
    # Alignment table reports the overlap shift of b relative to a
    assert isinstance(alignment, RecordTable)
    assert len(alignment) == 4
    quantities = {row["quantity"] for row in alignment}
    assert {"Overlap shift X (px)", "Overlap shift Y (px)", "Overlap shift X", "Overlap shift Y"} <= quantities
    for row in alignment:
        assert set(row) == {"quantity", "value", "unit"}


def test_stitch_below():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(data=np.ones((32, 32)))
    b = make_field(data=np.ones((32, 32)) * 2)
    result, alignment = node.process(a, b, "below", "none")
    assert result.data.shape[1] == 32
    assert result.data.shape[0] >= 32
    assert isinstance(alignment, RecordTable)
    assert len(alignment) == 4


def test_stitch_auto_direction():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(data=np.random.default_rng(0).standard_normal((32, 32)))
    b = make_field(data=np.random.default_rng(1).standard_normal((32, 32)))
    result, alignment = node.process(a, b, "auto", "linear")
    assert result.data.ndim == 2
    assert isinstance(alignment, RecordTable)
    assert len(alignment) == 4
    for row in alignment:
        assert row["unit"] == "px" or row["unit"] == a.si_unit_xy


def test_stitch_unknown_direction():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(shape=(16, 16))
    b = make_field(shape=(16, 16))
    with pytest.raises(ValueError):
        node.process(a, b, "unknown", "none")
