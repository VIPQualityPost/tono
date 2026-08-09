"""Image stitching — combine two overlapping scans into one image."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


def _find_overlap_shift(a: np.ndarray, b: np.ndarray) -> tuple[int, int]:
    """Estimate the (dy, dx) pixel shift of b relative to a via cross-correlation."""
    fa = np.fft.fft2(a - a.mean())
    fb = np.fft.fft2(b - b.mean())
    cross = np.fft.ifft2(fa * np.conj(fb))
    cc = np.abs(np.fft.fftshift(cross))
    cy, cx = np.array(cc.shape) // 2
    peak = np.unravel_index(np.argmax(cc), cc.shape)
    dy = peak[0] - cy
    dx = peak[1] - cx
    return int(dy), int(dx)


def _blend_overlap(a: np.ndarray, b: np.ndarray, axis: int) -> np.ndarray:
    """Linear blend along the overlap axis."""
    length = a.shape[axis]
    weight = np.linspace(1.0, 0.0, length)
    if axis == 0:
        weight = weight[:, np.newaxis]
    return a * weight + b * (1.0 - weight)


@register_node(display_name="Image Stitch")
class ImageStitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "direction": (["right", "below", "auto"], {"default": "auto"}),
                "blend": (["linear", "none"], {"default": "linear"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'stitched'),
        ('RECORD_TABLE', 'alignment'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Combine two overlapping scans into a single image. "
        "Uses cross-correlation to align the images and blends the overlap region. "
        "Direction specifies how field_b is positioned relative to field_a. "
        "'auto' uses cross-correlation to determine the best placement. "
    )

    KEYWORDS = ("mosaic", "merge", "combine", "panorama", "blend")

    def process(self, field_a: DataField, field_b: DataField, direction: str, blend: str) -> tuple:
        a = np.asarray(field_a.data, dtype=np.float64)
        b = np.asarray(field_b.data, dtype=np.float64)

        if direction == "auto":
            # Pad b to match a's shape for cross-correlation
            shape = (max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1]))
            a_pad = np.zeros(shape)
            b_pad = np.zeros(shape)
            a_pad[:a.shape[0], :a.shape[1]] = a
            b_pad[:b.shape[0], :b.shape[1]] = b
            dy, dx = _find_overlap_shift(a_pad, b_pad)
            direction = "right" if abs(dx) >= abs(dy) else "below"

        if direction == "right":
            # b is to the right of a
            dy, dx = _find_overlap_shift(
                a[:, -min(a.shape[1], b.shape[1]):],
                b[:, :min(a.shape[1], b.shape[1])],
            )
            overlap = max(0, min(a.shape[1], b.shape[1]) - abs(dx))
            if overlap <= 0:
                # No overlap, just concatenate
                out_h = max(a.shape[0], b.shape[0])
                out = np.zeros((out_h, a.shape[1] + b.shape[1]))
                out[:a.shape[0], :a.shape[1]] = a
                out[:b.shape[0], a.shape[1]:] = b
            else:
                out_h = max(a.shape[0], b.shape[0])
                out_w = a.shape[1] + b.shape[1] - overlap
                out = np.zeros((out_h, out_w))
                out[:a.shape[0], :a.shape[1]] = a
                b_start = a.shape[1] - overlap
                if blend == "linear" and overlap > 1:
                    ov_a = a[:min(a.shape[0], b.shape[0]), a.shape[1] - overlap:]
                    ov_b = b[:min(a.shape[0], b.shape[0]), :overlap]
                    blended = _blend_overlap(ov_a, ov_b, axis=1)
                    out[:blended.shape[0], b_start:b_start + overlap] = blended
                    out[:b.shape[0], b_start + overlap:b_start + b.shape[1]] = b[:, overlap:]
                else:
                    out[:b.shape[0], b_start:b_start + b.shape[1]] = b

        elif direction == "below":
            dy, dx = _find_overlap_shift(
                a[-min(a.shape[0], b.shape[0]):, :],
                b[:min(a.shape[0], b.shape[0]), :],
            )
            overlap = max(0, min(a.shape[0], b.shape[0]) - abs(dy))
            if overlap <= 0:
                out_w = max(a.shape[1], b.shape[1])
                out = np.zeros((a.shape[0] + b.shape[0], out_w))
                out[:a.shape[0], :a.shape[1]] = a
                out[a.shape[0]:, :b.shape[1]] = b
            else:
                out_w = max(a.shape[1], b.shape[1])
                out_h = a.shape[0] + b.shape[0] - overlap
                out = np.zeros((out_h, out_w))
                out[:a.shape[0], :a.shape[1]] = a
                b_start = a.shape[0] - overlap
                if blend == "linear" and overlap > 1:
                    ov_a = a[a.shape[0] - overlap:, :min(a.shape[1], b.shape[1])]
                    ov_b = b[:overlap, :min(a.shape[1], b.shape[1])]
                    blended = _blend_overlap(ov_a, ov_b, axis=0)
                    out[b_start:b_start + overlap, :blended.shape[1]] = blended
                    out[b_start + overlap:b_start + b.shape[0], :b.shape[1]] = b[overlap:, :]
                else:
                    out[b_start:b_start + b.shape[0], :b.shape[1]] = b
        else:
            raise ValueError(f"Unknown direction: {direction!r}")

        xreal = out.shape[1] * field_a.dx
        yreal = out.shape[0] * field_a.dy

        # Overlap shift of b relative to a from the last cross-correlation
        alignment = RecordTable([
            {"quantity": "Overlap shift X (px)", "value": float(dx), "unit": "px"},
            {"quantity": "Overlap shift Y (px)", "value": float(dy), "unit": "px"},
            {"quantity": "Overlap shift X", "value": float(dx) * field_a.dx, "unit": field_a.si_unit_xy},
            {"quantity": "Overlap shift Y", "value": float(dy) * field_a.dy, "unit": field_a.si_unit_xy},
        ])
        emit_table(alignment)
        return (field_a.replace(data=out, xreal=xreal, yreal=yreal), alignment)
