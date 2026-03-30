import math
from backend.data_types import RecordTable
from backend.execution_context import active_node, execution_callbacks


def test_value_display():
    from backend.nodes.value_io import ValueIO

    node = ValueIO()
    value_spec = ValueIO.INPUT_TYPES()["optional"]["value"]
    assert value_spec[0] == "FLOAT"
    assert value_spec[1]["accepted_types"] == ["RECORD_TABLE"]

    captured = []
    ValueIO._broadcast_value_fn = lambda node_id, payload: captured.append((node_id, payload))
    ValueIO._current_node_id = "test"

    result = node.display_value(value=3.25)
    assert result == (3.25,)
    assert captured == [("test", {"value": 3.25})]

    measurements = RecordTable([
        {"quantity": "delta X", "value": 1.7e-7, "unit": "m"},
        {"quantity": "delta Y", "value": 463, "unit": "count"},
    ])
    result = node.display_value(value=measurements, measurement="delta X")
    assert result == (1.7e-7,)
    assert captured[-1] == ("test", {"value": 1.7e-7, "unit": "m"})

    ValueIO._broadcast_value_fn = None


def test_value_display_string_input():
    from backend.nodes.value_io import ValueIO

    node = ValueIO()
    values = []
    with execution_callbacks(value=lambda nid, v: values.append(v)), active_node("n1"):
        # plain number
        result = node.display_value(number_input="42")
    assert result == (42.0,)
    assert values[-1]["value"] == 42.0

    values.clear()
    with execution_callbacks(value=lambda nid, v: values.append(v)), active_node("n1"):
        # negative number
        result = node.display_value(number_input="-3.14")
    assert math.isclose(result[0], -3.14)
    assert math.isclose(values[-1]["value"], -3.14)


def test_value_display_table_emits_table():
    from backend.nodes.value_io import ValueIO

    node = ValueIO()
    tables = []
    measurements = RecordTable([
        {"quantity": "Rq", "value": 0.42, "unit": "nm"},
    ])
    with execution_callbacks(table=lambda nid, t: tables.append(t)), active_node("n1"):
        result = node.display_value(value=measurements, measurement="Rq")
    assert result == (0.42,)
    assert len(tables) == 1
    assert tables[0][0]["quantity"] == "Rq"
