import json
import numpy as np
from backend.data_types import DataField, LineData


def test_curvature():
    from backend.node_registry import get_node_info
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.curvature import Curvature

    node = Curvature()
    assert get_node_info("Curvature")["category"] == "Measure"

    xres, yres = 121, 101
    xreal, yreal = 8.0e-6, 6.0e-6
    xoff, yoff = 1.0e-6, -0.5e-6
    x = np.linspace(xoff, xoff + xreal, xres, dtype=np.float64)
    y = np.linspace(yoff, yoff + yreal, yres, dtype=np.float64)
    yy, xx = np.meshgrid(y, x, indexing="ij")

    x0 = xoff + 0.45 * xreal
    y0 = yoff + 0.60 * yreal
    rx = 1.2e-6
    ry = 2.4e-6
    z0 = 3.0e-9
    data = z0 + (xx - x0) ** 2 / (2.0 * rx) + (yy - y0) ** 2 / (2.0 * ry)
    field = DataField(data=data, xreal=xreal, yreal=yreal, xoff=xoff, yoff=yoff, si_unit_xy="m", si_unit_z="m")

    previews = []
    tables = []
    with execution_callbacks(preview=lambda nid, uri: previews.append(uri), table=lambda nid, rows: tables.append(rows)), active_node("test"):
        output, table, profile1, profile2 = node.process(field, masking="ignore")

    rows = {row["quantity"]: row for row in table}
    recovered_radii = sorted([rows["Curvature radius 1"]["value"], rows["Curvature radius 2"]["value"]])
    expected_radii = sorted([rx, ry])
    assert len(previews) == 1
    assert isinstance(previews[0], dict) and previews[0].get("kind") == "panels"
    assert len(tables) == 1
    assert abs(rows["Center x position"]["value"] - x0) < xreal * 0.02
    assert abs(rows["Center y position"]["value"] - y0) < yreal * 0.02
    assert abs(rows["Center value"]["value"] - z0) < 5e-11
    assert np.allclose(recovered_radii, expected_radii, rtol=0.08, atol=5e-8)
    assert output.overlays[-1]["kind"] == "markup"
    assert len(output.overlays[-1]["shapes"]) == 3
    assert isinstance(profile1, LineData)
    assert isinstance(profile2, LineData)
    assert profile1.x_unit == field.si_unit_xy
    assert profile1.y_unit == field.si_unit_z
    assert len(profile1) > 10
    assert len(profile2) > 10

    mask = np.zeros((yres, xres), dtype=np.uint8)
    mask[:, :xres // 2] = 255
    left = 1.0e-9 + (xx - (xoff + 0.25 * xreal)) ** 2 / (2.0 * 0.9e-6) + (yy - (yoff + 0.5 * yreal)) ** 2 / (2.0 * 1.8e-6)
    right = 2.0e-9 + (xx - (xoff + 0.75 * xreal)) ** 2 / (2.0 * 1.6e-6) + (yy - (yoff + 0.5 * yreal)) ** 2 / (2.0 * 3.2e-6)
    split_field = DataField(data=np.where(mask > 0, left, right), xreal=xreal, yreal=yreal, xoff=xoff, yoff=yoff, si_unit_xy="m", si_unit_z="m")
    _, include_table, _, _ = node.process(split_field, masking="include", mask=mask)
    _, exclude_table, _, _ = node.process(split_field, masking="exclude", mask=mask)
    include_radii = sorted([row["value"] for row in include_table if row["quantity"].startswith("Curvature radius")])
    exclude_radii = sorted([row["value"] for row in exclude_table if row["quantity"].startswith("Curvature radius")])
    assert np.allclose(include_radii, [0.9e-6, 1.8e-6], rtol=0.12, atol=5e-8)
    assert np.allclose(exclude_radii, [1.6e-6, 3.2e-6], rtol=0.12, atol=5e-8)

    bad_units = DataField(data=np.zeros((16, 16), dtype=np.float64), xreal=1e-6, yreal=1e-6, si_unit_xy="nm", si_unit_z="V")
    try:
        node.process(bad_units, masking="ignore")
    except ValueError as exc:
        assert "compatible XY and Z units" in str(exc)
    else:
        assert False, "Curvature should reject incompatible XY/Z units."


def test_curvature_flat_surface():
    """A perfectly flat surface has zero curvature — both radii must be float('inf')."""
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.curvature import Curvature

    node = Curvature()
    data = np.zeros((64, 64), dtype=np.float64)
    field = DataField(data=data, xreal=1e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="m")

    warnings = []
    tables = []
    with execution_callbacks(
        preview=lambda nid, v: None,
        table=lambda nid, rows: tables.append(rows),
        warning=lambda nid, msg: warnings.append(msg),
    ), active_node("test"):
        _, table, _, _ = node.process(field, masking="ignore")

    rows = {row["quantity"]: row for row in table}
    assert rows["Curvature radius 1"]["value"] == float("inf")
    assert rows["Curvature radius 2"]["value"] == float("inf")
    assert len(warnings) == 0


def test_curvature_cylindrical():
    """A cylindrical surface is curved in one direction only — one radius finite, one inf."""
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.curvature import Curvature

    node = Curvature()
    N = 64
    xreal = yreal = 1e-6
    x = np.linspace(-xreal / 2, xreal / 2, N, dtype=np.float64)
    xx = np.broadcast_to(x, (N, N))
    r_x = 0.8e-6
    data = xx**2 / (2.0 * r_x)
    field = DataField(data=data, xreal=xreal, yreal=yreal, si_unit_xy="m", si_unit_z="m")

    tables = []
    with execution_callbacks(
        preview=lambda nid, v: None,
        table=lambda nid, rows: tables.append(rows),
    ), active_node("test"):
        _, table, _, _ = node.process(field, masking="ignore")

    rows = {row["quantity"]: row for row in table}
    radii = sorted([rows["Curvature radius 1"]["value"], rows["Curvature radius 2"]["value"]])
    finite = [r for r in radii if np.isfinite(r)]
    infinite = [r for r in radii if not np.isfinite(r)]
    assert len(finite) == 1, f"Expected 1 finite radius, got {radii}"
    assert len(infinite) == 1, f"Expected 1 inf radius, got {radii}"
    assert abs(finite[0] - r_x) < r_x * 0.1, f"Finite radius {finite[0]} far from expected {r_x}"


def test_curvature_too_few_pixels():
    """Curvature with fewer than 6 valid pixels emits a warning and returns an empty table."""
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.curvature import Curvature

    node = Curvature()
    N = 16
    data = np.random.default_rng(0).standard_normal((N, N))
    field = DataField(data=data, xreal=1e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="m")

    mask = np.zeros((N, N), dtype=np.uint8)
    mask[N // 2, N // 2:N // 2 + 4] = 255

    warnings = []
    tables = []
    with execution_callbacks(
        preview=lambda nid, v: None,
        table=lambda nid, rows: tables.append(rows),
        warning=lambda nid, msg: warnings.append(msg),
    ), active_node("test"):
        _, table, profile1, profile2 = node.process(field, masking="include", mask=mask)

    assert len(warnings) == 1
    assert "six" in warnings[0].lower() or "6" in warnings[0]
    assert len(list(table)) == 0
    assert len(profile1.data) == 0
    assert len(profile2.data) == 0


def test_curvature_inf_json_safe():
    """inf radii from curvature must not produce invalid JSON when sent over the wire."""
    from backend.server import _sanitize_non_finite, _dumps

    rows = [
        {"quantity": "Curvature radius 1", "value": float("inf"),  "unit": "m"},
        {"quantity": "Curvature radius 2", "value": float("-inf"), "unit": "m"},
        {"quantity": "Center value",        "value": float("nan"),  "unit": "m"},
        {"quantity": "Center x position",   "value": 1.5e-7,        "unit": "m"},
    ]

    sanitized = _sanitize_non_finite(rows)
    assert sanitized[0]["value"] == "∞"
    assert sanitized[1]["value"] == "-∞"
    assert sanitized[2]["value"] == "NaN"
    assert sanitized[3]["value"] == 1.5e-7

    payload = _dumps({"type": "table", "data": {"node_id": "n1", "rows": sanitized}})
    decoded = json.loads(payload)
    assert decoded["data"]["rows"][0]["value"] == "∞"
