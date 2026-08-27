import math
from backend.data_types import RecordTable
from backend.execution_context import active_node, execution_callbacks


def test_value_display():
    from backend.nodes.value_io import ValueIO

    node = ValueIO()
    value_spec = ValueIO.INPUT_TYPES()["optional"]["value"]
    assert value_spec[0] == "FLOAT"
    assert value_spec[1]["accepted_types"] == ["RECORD_TABLE"]

    from backend.execution_context import execution_callbacks, active_node
    captured = []
    with execution_callbacks(value=lambda nid, payload: captured.append((nid, payload))), active_node("test"):
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


def test_value_display_linked_table_passes_executor_coercion():
    """A RECORD_TABLE linked into the FLOAT 'value' socket must reach the node.

    Regression: strict input coercion rejected non-numeric values on FLOAT
    inputs even when the spec's ``accepted_types`` declare the socket
    polymorphic (e.g. ValueIO.display 'value' accepts RECORD_TABLE).
    """
    from backend.execution import ExecutionEngine, coerce_input_value
    from backend.nodes.value_io import ValueIO

    measurements = RecordTable([
        {"quantity": "Peak period", "value": 1.7e-7, "unit": "m"},
    ])
    value_spec = ValueIO.INPUT_TYPES()["optional"]["value"]

    # Linked table is passed through unchanged, ready for the node's own
    # measurement handling.
    assert coerce_input_value(measurements, value_spec, name="value") is measurements

    # Numeric widgets on the same polymorphic socket still coerce normally.
    assert coerce_input_value("2.5", value_spec, name="value") == 2.5

    # Engine link resolution (the executor code path for links).
    engine = ExecutionEngine()
    resolved = engine._resolve_inputs(
        {"value": ["upstream", 1]},
        {"upstream": (None, measurements)},
        input_types=ValueIO.INPUT_TYPES(),
    )
    assert resolved["value"] is measurements

    # Bare FLOAT inputs keep rejecting non-numeric garbage.
    with __import__("pytest").raises(ValueError, match="Expected a numeric value"):
        coerce_input_value(measurements, ("FLOAT", {"default": 0.0}), name="value")
