import numpy as np
from backend.data_types import RecordTable
from tests.node_tests._shared import make_field


def test_level_rotate_removes_tilt():
    from backend.nodes.level_rotate import LevelRotate

    node = LevelRotate()
    y, x = np.mgrid[:64, :64].astype(np.float64)
    data = 2.0 * x + 3.0 * y
    field = make_field(data=data)

    result, tilt = node.process(field)
    assert result.data.shape == data.shape
    assert result.data.std() < data.std() * 0.25
    # Tilt table reports the fitted slopes as angles in degrees
    assert isinstance(tilt, RecordTable)
    assert len(tilt) == 2
    quantities = {row["quantity"] for row in tilt}
    assert {"Tilt X", "Tilt Y"} == quantities
    for row in tilt:
        assert set(row) == {"quantity", "value", "unit"}
        assert row["unit"] == "deg"
        assert np.isfinite(row["value"])


def test_level_rotate_preserves_shape():
    from backend.nodes.level_rotate import LevelRotate

    node = LevelRotate()
    data = np.random.default_rng(42).standard_normal((48, 48))
    field = make_field(data=data)

    result, tilt = node.process(field)
    assert result.data.shape == (48, 48)
    assert isinstance(tilt, RecordTable)
    assert len(tilt) == 2


def test_level_rotate_flat_noop():
    from backend.nodes.level_rotate import LevelRotate

    node = LevelRotate()
    data = np.ones((32, 32)) * 7.0
    field = make_field(data=data)

    result, tilt = node.process(field)
    assert np.allclose(result.data, 7.0, atol=1e-6)
    # A flat plane has zero fitted tilt
    assert len(tilt) == 2
    assert abs(tilt[0]["value"]) < 1e-9
    assert abs(tilt[1]["value"]) < 1e-9
