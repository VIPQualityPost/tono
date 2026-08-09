"""Multiple profiles — extract and compare profiles from multiple images."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, LineData, datafield_to_uint8, encode_preview
from backend.execution_context import emit_overlay


def _blend_fields(field_a: DataField, field_b: DataField, alpha: float) -> np.ndarray:
    """Render field A with field B overlaid at `alpha` opacity (0=A only, 1=B only)."""
    a_rgb = datafield_to_uint8(field_a, field_a.colormap).astype(np.float32)
    b_rgb = datafield_to_uint8(field_b, field_b.colormap).astype(np.float32)
    wa = 1.0 - alpha
    wb = alpha
    if b_rgb.shape != a_rgb.shape:
        h = min(a_rgb.shape[0], b_rgb.shape[0])
        w = min(a_rgb.shape[1], b_rgb.shape[1])
        canvas = a_rgb.copy()
        canvas[:h, :w] = wa * a_rgb[:h, :w] + wb * b_rgb[:h, :w]
        return canvas.astype(np.uint8)
    return (wa * a_rgb + wb * b_rgb).astype(np.uint8)


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
                "blend": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "slider": True}),
            }
        }

    OUTPUTS = (
        ('LINE', 'profile'),
        ('LINE', 'profile_b'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Extract and compare line profiles from two fields. "
        "Row=-1 uses the center row/column. Modes: overlay returns field_a's "
        "profile, mean averages both, difference subtracts b from a. "
        "Field B's raw profile is exposed as profile_b alongside the result. "
        "The preview shows field A blended with field B and highlights the "
        "row or column being sampled — drag to move the line."
    )

    KEYWORDS = ("line profile", "compare", "overlay", "cross section")

    def process(self, field_a: DataField, field_b: DataField,
                row: int, direction: str, mode: str, blend: float = 0.5) -> tuple:
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
            line_axis_max = a.shape[0] - 1
        else:
            if row < 0:
                row = a.shape[1] // 2
            row = min(row, a.shape[1] - 1, b.shape[1] - 1)
            pa = a[:, row]
            pb = b[:min(a.shape[0], b.shape[0]), row]
            pa = pa[:len(pb)]
            dx = field_a.dy
            x_unit = field_a.si_unit_xy
            line_axis_max = a.shape[1] - 1

        x_axis = np.arange(len(pa)) * dx

        if mode == "overlay":
            result = pa
        elif mode == "mean":
            result = 0.5 * (pa + pb)
        elif mode == "difference":
            result = pa - pb
        else:
            result = pa

        alpha = float(np.clip(blend, 0.0, 1.0))
        emit_overlay({
            "kind": "multi_profile",
            "section_title": "Preview",
            "image": encode_preview(_blend_fields(field_a, field_b, alpha)),
            "row": int(row),
            "direction": direction,
            "max_index": int(line_axis_max),
        })

        profile = LineData(data=result, x_axis=x_axis, x_unit=x_unit,
                           y_unit=field_a.si_unit_z)
        profile_b = LineData(data=pb, x_axis=x_axis, x_unit=x_unit,
                             y_unit=field_a.si_unit_z)
        return (profile, profile_b)
