import numpy as np
from backend.data_types import LineData
from backend.node_registry import get_node_info
from backend.execution_context import active_node, execution_callbacks
from tests.node_tests._shared import make_field


def test_fractal_dimension():
    from backend.nodes.fractal_dimension import FractalDimension

    node = FractalDimension()
    assert get_node_info("FractalDimension")["category"] == "Measure"

    N = 129
    yy, xx = np.mgrid[0:N, 0:N] / (N - 1)
    data = 0.25 * xx + 0.12 * yy + 0.03 * np.sin(6.0 * np.pi * xx) + 0.02 * np.cos(4.0 * np.pi * yy)
    field = make_field(data=data, xreal=4.0e-6, yreal=4.0e-6)

    overlays = []
    tables = []
    with execution_callbacks(
        overlay=lambda nid, payload: overlays.append(payload),
        table=lambda nid, rows: tables.append(rows),
    ), active_node("test"):
        dimension, curve, table = node.process(
            field, method="partitioning", interpolation="linear", x1=0.0, y1=0.5, x2=1.0, y2=0.5,
        )

    assert np.isfinite(dimension)
    assert 1.5 < dimension < 2.5
    assert isinstance(curve, LineData)
    assert len(curve) > 3
    assert curve.x_axis is not None
    assert np.all(np.diff(curve.x_axis) > 0.0)
    assert len(overlays) == 1
    assert overlays[0]["kind"] == "line_plot"
    assert len(tables) == 1
    assert table[0]["quantity"] == "Dimension"

    methods = ["partitioning", "cube_counting", "triangulation", "psdf", "hhcf"]
    for method in methods:
        dim, line, measurements = node.process(
            field, method=method, interpolation="linear", x1=0.0, y1=0.5, x2=1.0, y2=0.5,
        )
        assert np.isfinite(dim), f"{method} should produce a finite fractal dimension"
        if method == "psdf":
            assert -1.0 < dim < 3.2
        else:
            assert 1.2 < dim < 3.2
        assert isinstance(line, LineData)
        assert len(line) >= 2
        assert measurements[0]["quantity"] == "Dimension"

    narrowed_dim, _, narrowed_table = node.process(
        field, method="partitioning", interpolation="linear", x1=0.15, y1=0.5, x2=0.55, y2=0.5,
    )
    assert np.isfinite(narrowed_dim)
    fit_from = next(row["value"] for row in narrowed_table if row["quantity"] == "Fit from")
    fit_to = next(row["value"] for row in narrowed_table if row["quantity"] == "Fit to")
    assert fit_to > fit_from
