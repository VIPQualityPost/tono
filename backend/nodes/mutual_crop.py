"""Mutual crop — align and crop two images to their overlapping region."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


@register_node(display_name="Mutual Crop")
class MutualCrop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'cropped_a'),
        ('DATA_FIELD', 'cropped_b'),
        ('RECORD_TABLE', 'alignment'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Align two images using cross-correlation and crop both to their "
        "overlapping region. Useful for comparing images acquired at "
        "different times or with slight position offsets. "
    )

    KEYWORDS = ("align", "overlap", "registration", "cross correlation", "match")

    def process(self, field_a: DataField, field_b: DataField) -> tuple:
        a = np.asarray(field_a.data, dtype=np.float64)
        b = np.asarray(field_b.data, dtype=np.float64)

        # Pad to common shape for cross-correlation
        shape = (max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1]))
        a_pad = np.zeros(shape)
        b_pad = np.zeros(shape)
        a_pad[:a.shape[0], :a.shape[1]] = a - a.mean()
        b_pad[:b.shape[0], :b.shape[1]] = b - b.mean()

        # Cross-correlate to find shift
        fa = np.fft.fft2(a_pad)
        fb = np.fft.fft2(b_pad)
        cc = np.abs(np.fft.ifft2(fa * np.conj(fb)))
        cc = np.fft.fftshift(cc)
        cy, cx = np.array(shape) // 2
        peak = np.unravel_index(np.argmax(cc), shape)
        dy = peak[0] - cy
        dx = peak[1] - cx

        # Alignment summary (shift of b relative to a), available on both return paths
        alignment = RecordTable([
            {"quantity": "Shift X (px)", "value": float(dx), "unit": "px"},
            {"quantity": "Shift Y (px)", "value": float(dy), "unit": "px"},
            {"quantity": "Shift X", "value": float(dx) * field_a.dx, "unit": field_a.si_unit_xy},
            {"quantity": "Shift Y", "value": float(dy) * field_a.dy, "unit": field_a.si_unit_xy},
        ])
        emit_table(alignment)

        # Compute overlap region
        ay_start = max(0, dy)
        ay_end = min(a.shape[0], b.shape[0] + dy)
        ax_start = max(0, dx)
        ax_end = min(a.shape[1], b.shape[1] + dx)

        by_start = max(0, -dy)
        by_end = by_start + (ay_end - ay_start)
        bx_start = max(0, -dx)
        bx_end = bx_start + (ax_end - ax_start)

        if ay_end <= ay_start or ax_end <= ax_start:
            # No overlap found, return originals
            return (field_a, field_b, alignment)

        crop_a = a[ay_start:ay_end, ax_start:ax_end]
        crop_b = b[by_start:by_end, bx_start:bx_end]

        # Crop origins: each cropped field keeps its physical position in its own frame
        xreal = crop_a.shape[1] * field_a.dx
        yreal = crop_a.shape[0] * field_a.dy
        crop_a_field = field_a.replace(
            data=crop_a,
            xreal=xreal,
            yreal=yreal,
            xoff=field_a.xoff + ax_start * field_a.dx,
            yoff=field_a.yoff + ay_start * field_a.dy,
        )
        crop_b_field = field_b.replace(
            data=crop_b,
            xreal=crop_b.shape[1] * field_b.dx,
            yreal=crop_b.shape[0] * field_b.dy,
            xoff=field_b.xoff + bx_start * field_b.dx,
            yoff=field_b.yoff + by_start * field_b.dy,
        )

        return (crop_a_field, crop_b_field, alignment)
