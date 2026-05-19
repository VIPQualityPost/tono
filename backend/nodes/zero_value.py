"""Zero Value — shift data so the mean or maximum equals zero."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Zero Mean")
class ZeroMean:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
    )
    FUNCTION = "process"

    DESCRIPTION = "Shift all values so the mean is exactly zero."

    KEYWORDS = ("offset", "center", "level", "mean")

    def process(self, field: DataField) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        return (field.replace(data=data - data.mean()),)


@register_node(display_name="Zero Maximum")
class ZeroMaximum:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
    )
    FUNCTION = "process"

    DESCRIPTION = "Shift all values so the maximum is exactly zero."

    KEYWORDS = ("offset", "level", "maximum")

    def process(self, field: DataField) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        return (field.replace(data=data - data.max()),)
