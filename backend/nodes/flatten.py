from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.nodes.helpers import normalize_mask, align_rows_to_landings
from backend.nodes.level_plane import _fit_plane


@register_node(display_name="Flatten")
class FlattenField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "masking": (["ignore", "include", "exclude"], {"default": "exclude"}),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'flattened'),
        ('RECORD_TABLE', 'plane'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit and subtract a least-squares plane, then re-offset every row so its "
        "usable (unmasked) pixels share one level. The row alignment removes "
        "per-row scan DC offsets that no single plane can represent, recovering "
        "a flat grating from raw unleveled rows. Mask the pits (exclude) so they "
        "do not bias the background fit."
    )

    KEYWORDS = ("flatten", "plane", "level", "rows", "grating", "tilt", "background")

    def process(
        self,
        field: DataField,
        masking: str = "exclude",
        mask: np.ndarray | None = None,
    ) -> tuple:
        data = field.data.copy()
        mask_array = normalize_mask(mask, data.shape)
        pa, pbx, pby, xx, yy = _fit_plane(data, mask_array, masking)
        plane = pa + pbx * xx + pby * yy
        flattened = align_rows_to_landings(data - plane, mask_array, masking)

        tilt_x_deg = float(np.degrees(np.arctan(pbx / field.xreal))) if field.xreal > 0 else float(np.degrees(np.arctan(pbx)))
        tilt_y_deg = float(np.degrees(np.arctan(pby / field.yreal))) if field.yreal > 0 else float(np.degrees(np.arctan(pby)))
        plane_table = RecordTable([
            {"quantity": "Plane offset", "value": pa, "unit": field.si_unit_z},
            {"quantity": "Tilt X", "value": tilt_x_deg, "unit": "deg"},
            {"quantity": "Tilt Y", "value": tilt_y_deg, "unit": "deg"},
        ])
        emit_table(plane_table)
        return (field.replace(data=flattened), plane_table)