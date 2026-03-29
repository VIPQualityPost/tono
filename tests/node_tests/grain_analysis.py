import numpy as np
from tests.node_tests._shared import make_field


def test_grain_analysis():
    from backend.nodes.grain_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 64
    data = np.zeros((N, N))
    data[5:15, 5:15] = 5.0
    data[45:53, 45:53] = 3.0
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    mask = np.zeros((N, N), dtype=np.uint8)
    mask[5:15, 5:15] = 255
    mask[45:53, 45:53] = 255

    table, = node.process(field, mask=mask, min_size=10)
    assert len(table) == 2, f"Expected 2 grains, got {len(table)}"

    table.sort(key=lambda r: r["area_px"], reverse=True)
    assert table[0]["area_px"] == 100
    assert table[1]["area_px"] == 64
    assert abs(table[0]["mean_height"] - 5.0) < 1e-10
    assert abs(table[1]["mean_height"] - 3.0) < 1e-10
    assert table[0]["area_px_unit"] == "px^2"
    assert table[0]["area_m2_unit"] == "m^2"
    assert table[0]["equiv_diam_m_unit"] == "m"
    assert table[0]["mean_height_unit"] == "m"
    assert table[0]["max_height_unit"] == "m"

    table_filtered, = node.process(field, mask=mask, min_size=80)
    assert len(table_filtered) == 1
    assert table_filtered[0]["area_px"] == 100
