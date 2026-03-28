from __future__ import annotations

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.spectral_common import acf_field_from_data, preprocess_spectral_data


@register_node(display_name="ACF")
class ACF:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "level": (["mean", "plane", "none"], {"default": "mean"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'acf'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the two-dimensional autocorrelation function with Gwyddion-style "
        "mean or plane levelling before correlation. The output is centered on zero shift "
        "and uses the default half-range extents from acf2d."
    )

    def process(self, field: DataField, level: str) -> tuple:
        data = preprocess_spectral_data(field, level=level, windowing="none")
        return (acf_field_from_data(field, data),)
