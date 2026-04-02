def test_print_table():
    from backend.nodes.print_table import PrintTable
    from backend.execution_context import execution_callbacks, active_node
    node = PrintTable()

    table_spec = PrintTable.INPUT_TYPES()["required"]["table"]
    assert table_spec[0] == "RECORD_TABLE"
    assert table_spec[1]["accepted_types"] == ["DATA_TABLE"]

    captured = []
    with execution_callbacks(table=lambda nid, rows: captured.append(rows)), active_node("test"):
        table = [{"quantity": "test", "value": 42.0, "unit": "m"}]
        node.print_table(table=table)
        assert len(captured) == 1
        assert captured[0] == table
