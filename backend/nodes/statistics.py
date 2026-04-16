from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.nodes.helpers import mask_to_bool


@register_node(display_name="Statistics")
class Statistics:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('RECORD_TABLE', 'stats'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute basic surface statistics: min, max, mean, RMS roughness, median, "
        "and skewness. When a mask is provided, only pixels inside the mask are "
        "included."
    )

    KEYWORDS = ("mean", "rms", "min", "max", "skewness", "kurtosis", "median", "roughness")

    def process(self, field: DataField, mask: np.ndarray | None = None) -> tuple:
        d = field.data
        if mask is not None:
            selector = mask_to_bool(mask)
            if selector.shape != d.shape:
                raise ValueError(
                    f"Mask shape {selector.shape} does not match field shape {d.shape}"
                )
            d = d[selector]
            if d.size == 0:
                raise ValueError("Mask selects no pixels")

        mean = float(d.mean())
        rms = float(np.sqrt(np.mean((d - mean) ** 2)))
        skewness = float(np.mean(((d - mean) / rms) ** 3)) if rms > 0 else 0.0
        kurtosis = float(np.mean(((d - mean) / rms) ** 4)) if rms > 0 else 0.0

        table = RecordTable([
            {"quantity": "min",      "value": float(d.min()),    "unit": field.si_unit_z},
            {"quantity": "max",      "value": float(d.max()),    "unit": field.si_unit_z},
            {"quantity": "mean",     "value": mean,              "unit": field.si_unit_z},
            {"quantity": "RMS",      "value": rms,               "unit": field.si_unit_z},
            {"quantity": "median",   "value": float(np.median(d)), "unit": field.si_unit_z},
            {"quantity": "skewness", "value": skewness,          "unit": ""},
            {"quantity": "kurtosis", "value": kurtosis,          "unit": ""},
            {"quantity": "range",    "value": float(d.max() - d.min()), "unit": field.si_unit_z},
        ])
        return (table,)
