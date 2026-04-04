"""Mutual crop — align and crop two images to their overlapping region."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


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
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Align two images using cross-correlation and crop both to their "
        "overlapping region. Useful for comparing images acquired at "
        "different times or with slight position offsets. "
    )

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
            return (field_a, field_b)

        crop_a = a[ay_start:ay_end, ax_start:ax_end]
        crop_b = b[by_start:by_end, bx_start:bx_end]

        xreal = crop_a.shape[1] * field_a.dx
        yreal = crop_a.shape[0] * field_a.dy

        return (
            field_a.replace(data=crop_a, xreal=xreal, yreal=yreal),
            field_b.replace(data=crop_b, xreal=xreal, yreal=yreal),
        )
