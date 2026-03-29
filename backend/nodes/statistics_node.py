from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Statistics")
class Statistics:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('RECORD_TABLE', 'stats'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute basic surface statistics: min, max, mean, RMS roughness, median, "
        "and skewness. Equivalent to gwy_data_field_get_min/max/avg/rms."
    )

    def process(self, field: DataField) -> tuple:
        d = field.data
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
