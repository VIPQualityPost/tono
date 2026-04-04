"""Multiple profiles — extract and compare profiles from multiple images."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, LineData


@register_node(display_name="Multiple Profiles")
class MultipleProfiles:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "row": ("INT", {"default": -1, "min": -1, "max": 10000, "step": 1}),
                "direction": (["horizontal", "vertical"], {"default": "horizontal"}),
                "mode": (["overlay", "mean", "difference"], {"default": "overlay"}),
            }
        }

    OUTPUTS = (
        ('LINE_DATA', 'profile'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Extract and compare line profiles from two fields. "
        "Row=-1 uses the center row/column. Modes: overlay returns field_a's "
        "profile, mean averages both, difference subtracts b from a. "
    )

    def process(self, field_a: DataField, field_b: DataField,
                row: int, direction: str, mode: str) -> tuple:
        a = np.asarray(field_a.data, dtype=np.float64)
        b = np.asarray(field_b.data, dtype=np.float64)

        if direction == "horizontal":
            if row < 0:
                row = a.shape[0] // 2
            row = min(row, a.shape[0] - 1, b.shape[0] - 1)
            pa = a[row, :]
            pb = b[row, :min(a.shape[1], b.shape[1])]
            pa = pa[:len(pb)]
            dx = field_a.dx
            x_unit = field_a.si_unit_xy
        else:
            if row < 0:
                row = a.shape[1] // 2
            row = min(row, a.shape[1] - 1, b.shape[1] - 1)
            pa = a[:, row]
            pb = b[:min(a.shape[0], b.shape[0]), row]
            pa = pa[:len(pb)]
            dx = field_a.dy
            x_unit = field_a.si_unit_xy

        x_axis = np.arange(len(pa)) * dx

        if mode == "overlay":
            result = pa
        elif mode == "mean":
            result = 0.5 * (pa + pb)
        elif mode == "difference":
            result = pa - pb
        else:
            result = pa

        return (LineData(data=result, x_axis=x_axis, x_unit=x_unit,
                         y_unit=field_a.si_unit_z),)
