"""Level Rotate — level by physically rotating the data plane."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


@register_node(display_name="Level Rotate")
class LevelRotate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
        ('RECORD_TABLE', 'tilt'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Level by physically rotating the data plane. Fits a best-fit plane, "
        "converts its slopes to tilt angles, then rotates the surface by "
        "those angles using interpolation rather than algebraic subtraction."
    )

    KEYWORDS = ("rotate", "tilt", "level", "plane")

    def process(self, field: DataField) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Fit plane: z = a + bx*x + by*y (x,y in pixel coords)
        yy, xx = np.mgrid[:yres, :xres].astype(np.float64)
        A = np.column_stack([np.ones(yres * xres), xx.ravel(), yy.ravel()])
        coeffs, _, _, _ = np.linalg.lstsq(A, data.ravel(), rcond=None)
        _, bx, by = coeffs

        # Convert pixel slopes to tilt angles
        alpha_x = np.arctan(bx)
        alpha_y = np.arctan(by)

        # Build rotation: for each output pixel, find where it came from
        cx = (xres - 1) / 2.0
        cy = (yres - 1) / 2.0

        cos_x = np.cos(alpha_x)
        cos_y = np.cos(alpha_y)

        # Source coordinates after removing tilt
        src_x = xx.copy()
        src_y = yy.copy()
        src_z = data.copy()

        # Rotate about x-axis (corrects y-tilt)
        dy = yy - cy
        src_y_rot = cy + dy * cos_y
        src_z = src_z - dy * np.sin(alpha_y)

        # Rotate about y-axis (corrects x-tilt)
        dx = xx - cx
        src_x_rot = cx + dx * cos_x
        src_z = src_z - dx * np.sin(alpha_x)

        # Resample with the adjusted z values
        result = map_coordinates(src_z, [src_y_rot, src_x_rot], order=1,
                                 mode='nearest')

        tilt = RecordTable([
            {"quantity": "Tilt X", "value": float(np.degrees(alpha_x)), "unit": "deg"},
            {"quantity": "Tilt Y", "value": float(np.degrees(alpha_y)), "unit": "deg"},
        ])
        emit_table(tilt)
        return (field.replace(data=result), tilt)
