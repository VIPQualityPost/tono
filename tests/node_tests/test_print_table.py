def test_print_table():
    from backend.nodes.print_table import PrintTable
    node = PrintTable()

    table_spec = PrintTable.INPUT_TYPES()["required"]["table"]
    assert table_spec[0] == "RECORD_TABLE"
    assert table_spec[1]["accepted_types"] == ["DATA_TABLE"]

    captured = []
    PrintTable._broadcast_table_fn = lambda node_id, rows: captured.append(rows)
    PrintTable._current_node_id = "test"

    table = [{"quantity": "test", "value": 42.0, "unit": "m"}]
    node.print_table(table=table)
    assert len(captured) == 1
    assert captured[0] == table

    PrintTable._broadcast_table_fn = None
