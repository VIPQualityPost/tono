from __future__ import annotations
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Gaussian Filter")
class GaussianFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "sigma": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 50.0, "step": 0.1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filtered'),
    )
    FUNCTION = "process"

    DESCRIPTION = "Apply a Gaussian blur."
    
    def process(self, field: DataField, sigma: float) -> tuple:
        from scipy.ndimage import gaussian_filter
        data = gaussian_filter(field.data, sigma=float(sigma))
        return (field.replace(data=data),)
