from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Local Contrast")
class LocalContrast:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "kernel_size": ("INT", {"default": 10, "min": 2, "max": 100}),
                "weight": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Expand the local dynamic range at each pixel. "
        "Reveals fine surface features that are hidden by global contrast range. "
    )

    def process(self, field: DataField, kernel_size: int, weight: float) -> tuple:
        from scipy.ndimage import minimum_filter, maximum_filter

        data = np.asarray(field.data, dtype=np.float64)
        kernel_size = max(2, int(kernel_size))
        weight = float(np.clip(weight, 0.0, 1.0))

        local_min = minimum_filter(data, size=kernel_size, mode="reflect")
        local_max = maximum_filter(data, size=kernel_size, mode="reflect")

        global_min = float(data.min())
        global_max = float(data.max())

        local_range = local_max - local_min
        eps = np.finfo(np.float64).eps * max(abs(global_max), abs(global_min), 1.0)

        # Remap each pixel from its local range to the global range.
        # Where local_range is near zero, the pixel is already flat: leave it
        # unchanged (enhancement factor = 1).
        safe_range = np.where(local_range > eps, local_range, 1.0)
        global_span = global_max - global_min
        if global_span <= eps:
            # Uniform field – nothing to enhance.
            return (field.replace(data=data.copy()),)

        enhancement_factor = global_span / safe_range
        # Locally enhanced value: remap v from [local_min, local_max] → [global_min, global_max]
        v_enhanced = global_min + enhancement_factor * (data - local_min)

        # Blend between original and enhanced.
        result = (1.0 - weight) * data + weight * v_enhanced

        return (field.replace(data=result),)
