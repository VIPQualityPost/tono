from __future__ import annotations

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.spectral_common import preprocess_spectral_data, psdf_field_from_data


@register_node(display_name="PSDF")
class PSDF:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "windowing": (["hann", "hamming", "blackman", "none"], {"default": "hann"}),
                "level": (["mean", "plane", "none"], {"default": "mean"}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("psdf",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the two-dimensional power spectral density function with Gwyddion-style "
        "window RMS compensation and centered zero frequency. Equivalent to psdf2d / "
        "gwy_data_field_2dpsdf."
    )

    def process(self, field: DataField, windowing: str, level: str) -> tuple:
        data = preprocess_spectral_data(field, level=level, windowing=windowing)
        return (psdf_field_from_data(field, data),)
