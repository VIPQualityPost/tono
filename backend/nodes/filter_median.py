from __future__ import annotations
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Median Filter")
class MedianFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "size": ("INT", {"default": 3, "min": 1, "max": 21, "step": 2}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filtered'),
    )
    FUNCTION = "process"

    DESCRIPTION = "Apply a median filter."

    def process(self, field: DataField, size: int) -> tuple:
        from scipy.ndimage import median_filter
        size = max(1, int(size))
        data = median_filter(field.data, size=size)
        return (field.replace(data=data),)
