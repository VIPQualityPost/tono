from backend.data_types import RecordTable


def test_value_display():
    from backend.nodes.value_io import ValueIO

    node = ValueIO()
    value_spec = ValueIO.INPUT_TYPES()["required"]["value"]
    assert value_spec[0] == "FLOAT"
    assert value_spec[1]["accepted_types"] == ["RECORD_TABLE"]

    captured = []
    ValueIO._broadcast_value_fn = lambda node_id, payload: captured.append((node_id, payload))
    ValueIO._current_node_id = "test"

    result = node.display_value(3.25)
    assert result == (3.25,)
    assert captured == [("test", {"value": 3.25})]

    measurements = RecordTable([
        {"quantity": "delta X", "value": 1.7e-7, "unit": "m"},
        {"quantity": "delta Y", "value": 463, "unit": "count"},
    ])
    result = node.display_value(measurements, measurement="delta X")
    assert result == (1.7e-7,)
    assert captured[-1] == ("test", {"value": 1.7e-7, "unit": "m"})

    ValueIO._broadcast_value_fn = None
