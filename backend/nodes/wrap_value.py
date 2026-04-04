"""Value wrapping — rewrap periodic values to different ranges."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Wrap Value")
class WrapValue:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "range": (["0_to_360", "neg180_to_180", "0_to_2pi", "neg_pi_to_pi", "custom"],
                          {"default": "0_to_360"}),
                "custom_min": ("FLOAT", {"default": 0.0, "min": -1e6, "max": 1e6, "step": 0.1}),
                "custom_max": ("FLOAT", {"default": 360.0, "min": -1e6, "max": 1e6, "step": 0.1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'wrapped'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Rewrap periodic values (phase, angle) to a specified range. "
        "Preset ranges for degrees and radians, or specify a custom range. "
    )

    KEYWORDS = ("phase", "angle", "modulo", "periodic", "degree", "radian", "unwrap", "rewrap")

    def process(self, field: DataField, range: str,
                custom_min: float, custom_max: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        ranges = {
            "0_to_360": (0.0, 360.0),
            "neg180_to_180": (-180.0, 180.0),
            "0_to_2pi": (0.0, 2 * np.pi),
            "neg_pi_to_pi": (-np.pi, np.pi),
        }

        if range == "custom":
            lo, hi = custom_min, custom_max
        else:
            lo, hi = ranges[range]

        period = hi - lo
        if period <= 0:
            return (field.replace(data=data),)

        wrapped = lo + (data - lo) % period
        return (field.replace(data=wrapped),)
