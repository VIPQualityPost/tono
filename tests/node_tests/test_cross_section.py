import numpy as np
from backend.data_types import LineData
from tests.node_tests._shared import make_field


def test_cross_section():
    from backend.nodes.cross_section import CrossSection
    node = CrossSection()

    N = 100
    y, x = np.mgrid[0:N, 0:N] / N
    data = x * 10.0
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    profile, marker_pair = node.process(field, x1=0.0, y1=0.5, x2=1.0, y2=0.5, extend="none", n_samples=100)
    assert isinstance(marker_pair, tuple) and len(marker_pair) == 2
    assert isinstance(profile, LineData)
    assert len(profile) == 100
    assert profile.x_unit == field.si_unit_xy
    assert profile.y_unit == field.si_unit_z
    assert np.isclose(profile.x_axis[0], 0.0)
    assert np.isclose(profile.x_axis[-1], field.xreal)
    assert profile[0] < 0.5
    assert profile[-1] > 9.5

    profile_auto, _ = node.process(field, x1=0.0, y1=0.5, x2=1.0, y2=0.5, extend="none", n_samples=0)
    assert len(profile_auto) >= 2

    profile_ext, _ = node.process(field, x1=0.3, y1=0.5, x2=0.7, y2=0.5, extend="to_edges", n_samples=100)
    assert profile_ext[0] < 0.5
    assert profile_ext[-1] > 9.5

    profile_diag, _ = node.process(field, x1=0.0, y1=0.0, x2=1.0, y2=1.0, extend="none", n_samples=50)
    assert len(profile_diag) == 50

    from backend.nodes.cursors import Cursors
    from backend.nodes.stats import Stats

    cursors = Cursors()
    table, _ = cursors.process(profile, x1=0.25, y1=0.5, x2=0.75, y2=0.5)
    rows = {row["quantity"]: row for row in table}
    assert rows["dx"]["unit"] == field.si_unit_xy
    assert rows["dy"]["unit"] == field.si_unit_z

    captured = []
    Stats._broadcast_value_fn = lambda nid, payload: captured.append(payload)
    Stats._current_node_id = "test"
    stats = Stats()
    mean_value, = stats.process(profile, operation="mean", column="value")
    assert mean_value > 0
    assert captured[-1]["unit"] == field.si_unit_z
    Stats._broadcast_value_fn = None
