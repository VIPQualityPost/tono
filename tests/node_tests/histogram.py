import numpy as np
from tests.node_tests._shared import make_field


def test_height_histogram():
    from backend.nodes.histogram import Histogram
    node = Histogram()

    data = np.linspace(0, 1, 1000).reshape(25, 40)
    field = make_field(data=data)

    from backend.execution_context import execution_callbacks, active_node
    overlays = []
    with execution_callbacks(overlay=lambda nid, data: overlays.append(data)), active_node("test"):
        table, coord_pair, curve = node.process(field, n_bins=10, y_scale="linear", x1=0.2, y1=0.5, x2=0.8, y2=0.5)
        assert isinstance(coord_pair, tuple) and len(coord_pair) == 2
        # LINE output carries one entry per bin, in the field's Z unit.
        assert len(curve.data) == 10
        assert np.all(np.isfinite(curve.data))
        assert curve.data.min() >= 0.0
        assert curve.x_unit == field.si_unit_z
        assert curve.y_unit == "count"
        measurements = {row["quantity"]: row for row in table}
        assert "A position" in measurements
        assert "A count" in measurements
        assert "B position" in measurements
        assert "B count" in measurements
        assert "delta X" in measurements
        assert "delta Y" in measurements
        assert measurements["A count"]["unit"] == "count"
        assert measurements["B count"]["unit"] == "count"
        assert measurements["B position"]["value"] > measurements["A position"]["value"]
        assert len(overlays) == 1
        assert overlays[0]["kind"] == "line_plot"
        assert overlays[0]["section_title"] == "Histogram"
        assert len(overlays[0]["line"]) == 10
        assert len(overlays[0]["x_axis"]) == 10
        assert np.isclose(overlays[0]["x1"], 0.2)
        assert np.isclose(overlays[0]["x2"], 0.8)
        assert np.isclose(
            measurements["delta Y"]["value"],
            measurements["B count"]["value"] - measurements["A count"]["value"],
        )
