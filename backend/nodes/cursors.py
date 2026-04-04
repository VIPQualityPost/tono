from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_overlay
from backend.data_types import DataField, LineData, RecordTable, encode_preview, render_datafield_preview
from backend.nodes.helpers import frac_to_index


@register_node(display_name="Cursors")
class Cursors:
    """Place two draggable cursors on a line plot or field to measure deltas."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "line": ("LINE", {
                    "label": "input",
                    "accepted_types": ["DATA_FIELD"],
                }),
                "x1": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
            },
            "optional": {
                "coord_pair": ("COORDPAIR", {"label": "coord pair"}),
            },
        }

    OUTPUTS = (
        ('RECORD_TABLE', 'measurement'),
        ('COORDPAIR', 'coord_pair'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Place two cursors on a line plot or 2D field. "
        "On lines it reports x/y positions and dx/dy. "
        "On fields it reports x/y/z at both markers plus dx/dy/dz."
    )

    KEYWORDS = ("marker", "distance", "measure", "delta", "ruler")

    def process(
        self, line, x1: float, y1: float, x2: float, y2: float,
        coord_pair=None,
    ) -> tuple:
        if coord_pair is not None:
            (x1, y1), (x2, y2) = coord_pair

        locked = coord_pair is not None

        if isinstance(line, DataField):
            return self._process_field(line, x1=x1, y1=y1, x2=x2, y2=y2, locked=locked)

        return self._process_line(line, x1=x1, y1=y1, x2=x2, y2=y2, locked=locked)

    def _process_line(
        self,
        line,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        locked: bool = False,
    ) -> tuple:
        y = np.asarray(line, dtype=np.float64).ravel()
        x_unit = line.x_unit if isinstance(line, LineData) else ""
        y_unit = line.y_unit if isinstance(line, LineData) else ""
        n = len(y)
        if isinstance(line, LineData) and line.x_axis is not None:
            x = np.asarray(line.x_axis, dtype=np.float64).ravel()[:n]
        else:
            x = np.arange(n, dtype=np.float64)
        x1 = float(np.clip(x1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 1.0))

        xmin = float(np.min(x)) if len(x) else 0.0
        xmax = float(np.max(x)) if len(x) else 1.0

        idx_a = frac_to_index(x, x1)
        idx_b = frac_to_index(x, x2)

        xa, ya = float(x[idx_a]), float(y[idx_a])
        xb, yb = float(x[idx_b]), float(y[idx_b])

        emit_overlay({
            "kind": "line_plot",
            "section_title": "Cursors",
            "line": y.tolist(),
            "x_axis": x.tolist(),
            "x_unit": x_unit,
            "x1": x1,
            "x2": x2,
            "y1": float(y1),
            "y2": float(y2),
            "a_locked": locked,
            "b_locked": locked,
        })

        length = float(np.hypot(xb - xa, yb - ya))
        table = RecordTable([
            {"quantity": "Length", "value": length,  "unit": x_unit},
            {"quantity": "dx",     "value": xb - xa, "unit": x_unit},
            {"quantity": "dy",  "value": yb - ya, "unit": y_unit},
            {"quantity": "A x", "value": xa, "unit": x_unit},
            {"quantity": "A y", "value": ya, "unit": y_unit},
            {"quantity": "B x", "value": xb, "unit": x_unit},
            {"quantity": "B y", "value": yb, "unit": y_unit},
        ])
        return (table, ((x1, y1), (x2, y2)))

    def _process_field(
        self,
        field: DataField,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        locked: bool = False,
    ) -> tuple:
        from scipy.ndimage import map_coordinates

        x1 = float(np.clip(x1, 0.0, 1.0))
        y1 = float(np.clip(y1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 1.0))
        y2 = float(np.clip(y2, 0.0, 1.0))

        px1 = x1 * max(field.xres - 1, 0)
        py1 = y1 * max(field.yres - 1, 0)
        px2 = x2 * max(field.xres - 1, 0)
        py2 = y2 * max(field.yres - 1, 0)

        z1 = float(map_coordinates(field.data, [[py1], [px1]], order=1, mode="nearest")[0])
        z2 = float(map_coordinates(field.data, [[py2], [px2]], order=1, mode="nearest")[0])

        ax = float(field.xoff + x1 * field.xreal)
        ay = float(field.yoff + y1 * field.yreal)
        bx = float(field.xoff + x2 * field.xreal)
        by = float(field.yoff + y2 * field.yreal)

        emit_overlay({
            "kind": "cursor_points",
            "section_title": "Cursors",
            "image": encode_preview(render_datafield_preview(field, field.colormap)),
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "a_locked": locked,
            "b_locked": locked,
        })

        table = RecordTable([
            {"quantity": "A x", "value": ax, "unit": field.si_unit_xy},
            {"quantity": "A y", "value": ay, "unit": field.si_unit_xy},
            {"quantity": "A z", "value": z1, "unit": field.si_unit_z},
            {"quantity": "B x", "value": bx, "unit": field.si_unit_xy},
            {"quantity": "B y", "value": by, "unit": field.si_unit_xy},
            {"quantity": "B z", "value": z2, "unit": field.si_unit_z},
            {"quantity": "dx", "value": bx - ax, "unit": field.si_unit_xy},
            {"quantity": "dy", "value": by - ay, "unit": field.si_unit_xy},
            {"quantity": "dz", "value": z2 - z1, "unit": field.si_unit_z},
        ])
        return (table, ((x1, y1), (x2, y2)))
