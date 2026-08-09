"""Immerse detail — overlay high-resolution detail onto lower-resolution overview."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


@register_node(display_name="Immerse Detail")
class ImmerseDetail:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "overview": ("DATA_FIELD",),
                "detail": ("DATA_FIELD",),
                "blend": (["replace", "average"], {"default": "replace"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'combined'),
        ('RECORD_TABLE', 'placement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Overlay a high-resolution detail scan onto a lower-resolution overview "
        "image using cross-correlation to find the best position. "
    )

    KEYWORDS = ("inset", "zoom", "merge", "overlay")

    def process(self, overview: DataField, detail: DataField, blend: str) -> tuple:
        ov = np.asarray(overview.data, dtype=np.float64)
        dt = np.asarray(detail.data, dtype=np.float64)

        # Resample detail to overview pixel size if needed
        scale_x = detail.dx / overview.dx
        scale_y = detail.dy / overview.dy

        if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
            from scipy.ndimage import zoom
            dt = zoom(dt, (scale_y, scale_x), order=1)

        dy_res, dx_res = dt.shape
        oy_res, ox_res = ov.shape

        # Placement summary; available on both return paths
        best_score = -np.inf
        best_y, best_x = 0, 0

        def build_table() -> RecordTable:
            return RecordTable([
                {"quantity": "Placement X (px)", "value": float(best_x), "unit": "px"},
                {"quantity": "Placement Y (px)", "value": float(best_y), "unit": "px"},
                {"quantity": "Placement X", "value": float(best_x) * overview.dx, "unit": overview.si_unit_xy},
                {"quantity": "Placement Y", "value": float(best_y) * overview.dy, "unit": overview.si_unit_xy},
                {"quantity": "Match score", "value": float(best_score), "unit": ""},
            ])

        if dy_res >= oy_res or dx_res >= ox_res:
            # Detail is larger than overview, just return overview
            placement = build_table()
            emit_table(placement)
            return (overview, placement)

        # Cross-correlate to find best position
        # Use a sliding window approach for small detail
        dt_norm = dt - dt.mean()
        dt_std = dt.std()
        if dt_std < 1e-30:
            dt_std = 1.0

        # Coarse search with stride
        stride = max(1, min(dy_res, dx_res) // 4)
        for iy in range(0, oy_res - dy_res + 1, stride):
            for ix in range(0, ox_res - dx_res + 1, stride):
                patch = ov[iy:iy + dy_res, ix:ix + dx_res]
                score = np.sum((patch - patch.mean()) * dt_norm) / (patch.std() * dt_std + 1e-30)
                if score > best_score:
                    best_score = score
                    best_y, best_x = iy, ix

        # Fine search around best position
        for iy in range(max(0, best_y - stride), min(oy_res - dy_res + 1, best_y + stride + 1)):
            for ix in range(max(0, best_x - stride), min(ox_res - dx_res + 1, best_x + stride + 1)):
                patch = ov[iy:iy + dy_res, ix:ix + dx_res]
                score = np.sum((patch - patch.mean()) * dt_norm) / (patch.std() * dt_std + 1e-30)
                if score > best_score:
                    best_score = score
                    best_y, best_x = iy, ix

        # Place detail into overview
        result = ov.copy()
        if blend == "replace":
            result[best_y:best_y + dy_res, best_x:best_x + dx_res] = dt
        else:  # average
            result[best_y:best_y + dy_res, best_x:best_x + dx_res] = \
                0.5 * (ov[best_y:best_y + dy_res, best_x:best_x + dx_res] + dt)

        placement = build_table()
        emit_table(placement)
        return (overview.replace(data=result), placement)
