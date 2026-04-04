"""Scan line reordering — fix meander, interlace, and deinterlace artifacts."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Scan Line Reorder")
class ScanLineReorder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "operation": (["reverse_odd", "reverse_even", "deinterlace_odd",
                               "deinterlace_even", "flip_vertical"], {"default": "reverse_odd"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fix scan line ordering artifacts. reverse_odd/even reverses alternate "
        "rows to correct meander (serpentine) scanning. deinterlace selects only "
        "odd or even rows and stretches to fill. flip_vertical reverses row order. "
    )

    def process(self, field: DataField, operation: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64).copy()
        yres, xres = data.shape

        if operation == "reverse_odd":
            data[1::2, :] = data[1::2, ::-1]
        elif operation == "reverse_even":
            data[0::2, :] = data[0::2, ::-1]
        elif operation == "deinterlace_odd":
            odd_rows = data[1::2, :]
            # Stretch back to original height via linear interpolation
            from scipy.ndimage import zoom
            scale_y = yres / odd_rows.shape[0]
            data = zoom(odd_rows, (scale_y, 1.0), order=1)
        elif operation == "deinterlace_even":
            even_rows = data[0::2, :]
            from scipy.ndimage import zoom
            scale_y = yres / even_rows.shape[0]
            data = zoom(even_rows, (scale_y, 1.0), order=1)
        elif operation == "flip_vertical":
            data = data[::-1, :].copy()
        else:
            raise ValueError(f"Unknown operation: {operation!r}")

        return (field.replace(data=data),)
