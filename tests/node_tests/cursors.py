import numpy as np
from backend.data_types import DataField, LineData


def test_line_cursors():
    from backend.nodes.cursors import Cursors

    node = Cursors()
    line_spec = Cursors.INPUT_TYPES()["required"]["line"]
    assert line_spec[0] == "LINE"
    assert line_spec[1]["accepted_types"] == ["DATA_FIELD"]

    line = np.linspace(0, 10, 100).astype(np.float64)

    from backend.execution_context import execution_callbacks, active_node
    overlays = []
    with execution_callbacks(overlay=lambda nid, data: overlays.append(data)), active_node("test"):
        table, coord_pair = node.process(line, x1=0.25, y1=0.5, x2=0.75, y2=0.5)
        assert isinstance(coord_pair, tuple) and len(coord_pair) == 2
        assert len(table) == 7
        quantities = {row["quantity"] for row in table}
        assert "Length" in quantities
        assert "A x" in quantities
        assert "B x" in quantities
        assert "dx" in quantities
        assert "dy" in quantities

        a_pos = next(r["value"] for r in table if r["quantity"] == "A x")
        b_pos = next(r["value"] for r in table if r["quantity"] == "B x")
        assert b_pos > a_pos

        dy = next(r["value"] for r in table if r["quantity"] == "dy")
        assert dy > 0

        assert len(overlays) == 1
        assert overlays[0]["kind"] == "line_plot"
        assert len(overlays[0]["line"]) == len(line)
        assert len(overlays[0]["x_axis"]) == len(line)
        assert 0.0 <= overlays[0]["x1"] <= 1.0
        assert 0.0 <= overlays[0]["x2"] <= 1.0

        line_data = LineData(data=line, x_axis=np.linspace(0, 1, 100))
        table2, _ = node.process(line_data, x1=0.25, y1=0.5, x2=0.75, y2=0.5)
        assert len(table2) == 7

        field = DataField(
            data=np.arange(100, dtype=np.float64).reshape(10, 10),
            xreal=2.0, yreal=4.0, si_unit_xy="um", si_unit_z="nm",
        )
        overlays.clear()
        table3, _ = node.process(field, x1=0.2, y1=0.25, x2=0.7, y2=0.75)
        assert len(table3) == 9
        field_rows = {row["quantity"]: row for row in table3}
        assert field_rows["dx"]["unit"] == "um"
        assert field_rows["dy"]["unit"] == "um"
        assert field_rows["dz"]["unit"] == "nm"
        assert np.isclose(field_rows["dx"]["value"], 1.0)
        assert np.isclose(field_rows["dy"]["value"], 2.0)
        assert len(overlays) == 1
        assert overlays[0]["kind"] == "cursor_points"
        assert overlays[0]["image"].startswith("data:image/png;base64,")
