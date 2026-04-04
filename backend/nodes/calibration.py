"""Calibration — apply lateral and height calibration corrections."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Calibration")
class Calibration:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "xy_mode": (["keep", "set_size", "scale"], {"default": "keep"}),
                "z_mode": (["keep", "set_range", "scale", "offset"], {"default": "keep"}),
                "xreal_new": ("FLOAT", {
                    "default": 1e-6,
                    "min": 1e-12,
                    "max": 1.0,
                    "step": 1e-9,
                    "show_when_widget_value": {"xy_mode": ["set_size"]},
                }),
                "yreal_new": ("FLOAT", {
                    "default": 1e-6,
                    "min": 1e-12,
                    "max": 1.0,
                    "step": 1e-9,
                    "show_when_widget_value": {"xy_mode": ["set_size"]},
                }),
                "xy_scale": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.001,
                    "max": 1000.0,
                    "step": 0.001,
                    "show_when_widget_value": {"xy_mode": ["scale"]},
                }),
                "z_min": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e-3,
                    "max": 1e-3,
                    "step": 1e-12,
                    "show_when_widget_value": {"z_mode": ["set_range"]},
                }),
                "z_max": ("FLOAT", {
                    "default": 1e-9,
                    "min": -1e-3,
                    "max": 1e-3,
                    "step": 1e-12,
                    "show_when_widget_value": {"z_mode": ["set_range"]},
                }),
                "z_scale": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.001,
                    "max": 1000.0,
                    "step": 0.001,
                    "show_when_widget_value": {"z_mode": ["scale"]},
                }),
                "z_offset": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e-3,
                    "max": 1e-3,
                    "step": 1e-12,
                    "show_when_widget_value": {"z_mode": ["offset"]},
                }),
                "xy_unit": ("STRING", {"default": ""}),
                "z_unit": ("STRING", {"default": ""}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply lateral and height calibration corrections to a DATA_FIELD. "
        "Lateral mode can set explicit physical size or scale uniformly. "
        "Height mode can rescale to a target range, multiply by a factor, "
        "or add a constant offset. Optionally override the XY or Z unit strings. "
        "Equivalent to Gwyddion's calibrate functionality."
    )

    KEYWORDS = ("units", "rescale", "dimensions")

    def process(
        self,
        field: DataField,
        xy_mode: str,
        z_mode: str,
        xreal_new: float,
        yreal_new: float,
        xy_scale: float,
        z_min: float,
        z_max: float,
        z_scale: float,
        z_offset: float,
        xy_unit: str,
        z_unit: str,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64).copy()
        xreal = float(field.xreal)
        yreal = float(field.yreal)
        si_unit_xy = field.si_unit_xy
        si_unit_z = field.si_unit_z

        # --- lateral calibration ---
        if xy_mode == "set_size":
            xreal = float(xreal_new)
            yreal = float(yreal_new)
        elif xy_mode == "scale":
            xreal *= float(xy_scale)
            yreal *= float(xy_scale)
        # "keep" → no change

        # --- height calibration ---
        if z_mode == "set_range":
            cur_min = float(data.min())
            cur_max = float(data.max())
            if cur_max > cur_min:
                data = float(z_min) + (data - cur_min) * (float(z_max) - float(z_min)) / (cur_max - cur_min)
            else:
                data[:] = float(z_min)
        elif z_mode == "scale":
            data *= float(z_scale)
        elif z_mode == "offset":
            data += float(z_offset)
        # "keep" → no change

        # --- unit overrides ---
        if xy_unit:
            si_unit_xy = xy_unit
        if z_unit:
            si_unit_z = z_unit

        return (field.replace(
            data=data,
            xreal=xreal,
            yreal=yreal,
            si_unit_xy=si_unit_xy,
            si_unit_z=si_unit_z,
        ),)
