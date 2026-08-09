from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.nodes.helpers import normalize_mask, apply_masking


def _fit_plane(
    data: np.ndarray,
    mask: np.ndarray | None,
    masking: str,
) -> tuple[float, float, float, np.ndarray, np.ndarray]:
    yres, xres = data.shape
    x = np.linspace(0.0, 1.0, xres)
    y = np.linspace(0.0, 1.0, yres)
    xx, yy = np.meshgrid(x, y)

    valid = apply_masking(data, mask, masking)

    if np.count_nonzero(valid) < 3:
        raise ValueError("Plane Level requires at least three usable pixels for fitting.")

    A = np.column_stack([
        np.ones(int(np.count_nonzero(valid)), dtype=np.float64),
        xx[valid].ravel(),
        yy[valid].ravel(),
    ])
    z = data[valid].ravel()
    coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
    pa, pbx, pby = coeffs
    return float(pa), float(pbx), float(pby), xx, yy


@register_node(display_name="Plane Level")
class PlaneLevelField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "masking": (["ignore", "include", "exclude"], {"default": "ignore"}),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
        ('RECORD_TABLE', 'plane'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit and subtract a least-squares plane from the data. Supports include/exclude mask fitting "
        "for flattening around features, similar to masked plane fitting workflows."
    )

    KEYWORDS = ("flatten", "tilt", "background")

    def process(
        self,
        field: DataField,
        masking: str = "ignore",
        mask: np.ndarray | None = None,
    ) -> tuple:
        data = field.data.copy()
        mask_array = normalize_mask(mask, data.shape)
        pa, pbx, pby, xx, yy = _fit_plane(data, mask_array, masking)

        plane = (pa + pbx * xx + pby * yy)

        tilt_x_deg = float(np.degrees(np.arctan(pbx / field.xreal))) if field.xreal > 0 else float(np.degrees(np.arctan(pbx)))
        tilt_y_deg = float(np.degrees(np.arctan(pby / field.yreal))) if field.yreal > 0 else float(np.degrees(np.arctan(pby)))
        plane_table = RecordTable([
            {"quantity": "Plane offset", "value": pa, "unit": field.si_unit_z},
            {"quantity": "Tilt X", "value": tilt_x_deg, "unit": "deg"},
            {"quantity": "Tilt Y", "value": tilt_y_deg, "unit": "deg"},
        ])
        emit_table(plane_table)
        return (field.replace(data=data - plane), plane_table)
