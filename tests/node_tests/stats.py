import numpy as np
from backend.data_types import DataTable, RecordTable
from tests.node_tests._shared import make_field


def test_stats():
    from backend.nodes.stats import Stats

    node = Stats()
    input_spec = Stats.INPUT_TYPES()["required"]["input"]
    assert input_spec[0] == "DATA_FIELD"
    assert input_spec[1]["accepted_types"] == ["IMAGE", "LINE", "DATA_TABLE"]

    captured = []
    Stats._broadcast_value_fn = lambda node_id, payload: captured.append((node_id, payload))
    Stats._current_node_id = "test"

    line = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    result, = node.process(line, operation="mean", column="value")
    assert np.isclose(result, 2.5)
    assert captured[-1] == ("test", {"value": result})
    roughness, = node.process(line, operation="Rq", column="value")
    assert np.isclose(roughness, np.sqrt(np.mean((line - line.mean()) ** 2)))

    table = DataTable([
        {"name": "a", "value": 3.0, "unit": "m", "other": 10.0},
        {"name": "b", "value": 7.0, "unit": "m", "other": 20.0},
    ])
    result, = node.process(table, operation="max", column="value")
    assert result == 7.0
    assert captured[-1] == ("test", {"value": 7.0, "unit": "m"})
    count, = node.process(table, operation="count", column="other")
    assert count == 2.0
    auto_column_range, = node.process(table, operation="range", column="")
    assert auto_column_range == 4.0

    field = make_field(data=np.array([[1.0, 5.0], [2.0, 4.0]], dtype=np.float64))
    result, = node.process(field, operation="range", column="value")
    assert result == 4.0
    assert captured[-1] == ("test", {"value": 4.0, "unit": "m"})

    image = np.array([[0, 10], [20, 30]], dtype=np.uint8)
    result, = node.process(image, operation="avg", column="value")
    assert np.isclose(result, 15.0)
    assert captured[-1] == ("test", {"value": 15.0})

    try:
        node.process(table, operation="Rq", column="value")
        raise AssertionError("Expected invalid TABLE operation to raise ValueError")
    except ValueError:
        pass

    try:
        node.process([{"label": "only text"}], operation="max", column="label")
        raise AssertionError("Expected non-numeric record-table input to raise ValueError")
    except ValueError:
        pass

    try:
        node.process(
            RecordTable([{"quantity": "min", "value": 1.0, "unit": "m"}]),
            operation="max", column="value",
        )
        raise AssertionError("Expected measurement table input to raise ValueError")
    except ValueError:
        pass

    Stats._broadcast_value_fn = None


def test_stats_empty_inputs():
    from backend.nodes.stats import Stats
    from backend.data_types import DataTable

    node = Stats()

    # empty record table (DataTable with no rows)
    try:
        node.process(DataTable([]), operation="mean", column="value")
        assert False, "Expected ValueError for empty table"
    except ValueError:
        pass

    # empty ndarray
    try:
        node.process(np.array([]), operation="mean", column="value")
        assert False, "Expected ValueError for empty ndarray"
    except ValueError:
        pass

    # empty LINE (1-D array)
    try:
        node.process(np.array([], dtype=np.float64), operation="Rq", column="value")
        assert False, "Expected ValueError for empty LINE"
    except ValueError:
        pass


def test_stats_unsupported_type():
    from backend.nodes.stats import Stats

    node = Stats()
    try:
        node.process("not_a_valid_input", operation="mean", column="value")
        assert False, "Expected ValueError for unsupported type"
    except ValueError:
        pass
