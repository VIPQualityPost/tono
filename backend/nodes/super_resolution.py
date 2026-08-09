"""Super-resolution -- combine multiple aligned scans for resolution enhancement."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import shift as ndimage_shift, zoom as ndimage_zoom

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


def _find_subpixel_shift(ref: np.ndarray, img: np.ndarray) -> tuple[float, float]:
    """Estimate the (dy, dx) sub-pixel shift of *img* relative to *ref* via cross-correlation.

    Uses FFT-based cross-correlation with parabolic peak refinement.
    """
    fa = np.fft.fft2(ref - ref.mean())
    fb = np.fft.fft2(img - img.mean())
    cross = np.fft.ifft2(fa * np.conj(fb))
    cc = np.abs(np.fft.fftshift(cross))

    cy, cx = np.array(cc.shape) // 2
    peak_y, peak_x = np.unravel_index(np.argmax(cc), cc.shape)

    # Integer shift relative to center
    dy = peak_y - cy
    dx = peak_x - cx

    # Parabolic sub-pixel refinement around peak
    h, w = cc.shape
    if 1 <= peak_y <= h - 2:
        num = float(cc[peak_y - 1, peak_x] - cc[peak_y + 1, peak_x])
        den = float(
            cc[peak_y - 1, peak_x] - 2.0 * cc[peak_y, peak_x] + cc[peak_y + 1, peak_x]
        )
        if abs(den) > 1e-12:
            dy += 0.5 * num / den

    if 1 <= peak_x <= w - 2:
        num = float(cc[peak_y, peak_x - 1] - cc[peak_y, peak_x + 1])
        den = float(
            cc[peak_y, peak_x - 1] - 2.0 * cc[peak_y, peak_x] + cc[peak_y, peak_x + 1]
        )
        if abs(den) > 1e-12:
            dx += 0.5 * num / den

    return float(dy), float(dx)


@register_node(display_name="Super Resolution")
class SuperResolution:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field1": ("DATA_FIELD",),
                "upscale": ("INT", {"default": 2, "min": 2, "max": 4, "step": 1}),
            },
            "optional": {
                "field2": ("DATA_FIELD",),
                "field3": ("DATA_FIELD",),
                "field4": ("DATA_FIELD",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
        ('RECORD_TABLE', 'alignment'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Combine multiple aligned scans to produce a super-resolved image with higher "
        "spatial resolution. Sub-pixel shifts between inputs are estimated via FFT "
        "cross-correlation and used to reconstruct a finer grid. When only one field "
        "is provided the image is upsampled using cubic interpolation. The "
        "estimated per-frame sub-pixel shifts are reported as an alignment table."
    )

    KEYWORDS = ("upscale", "upsample", "multiframe", "stack", "subpixel", "enhance")

    def process(
        self,
        field1: DataField,
        upscale: int,
        field2: DataField | None = None,
        field3: DataField | None = None,
        field4: DataField | None = None,
    ) -> tuple:
        fields = [field1]
        for f in (field2, field3, field4):
            if f is not None:
                fields.append(f)

        ref = np.asarray(field1.data, dtype=np.float64)

        # Upsample reference to target resolution
        high_res = ndimage_zoom(ref, upscale, order=3)
        weight = np.ones_like(high_res)

        alignment = RecordTable()

        if len(fields) == 1:
            # Single input -- just return the upsampled reference
            emit_table(alignment)
            return (field1.replace(
                data=high_res,
                xreal=field1.xreal,
                yreal=field1.yreal,
            ), alignment)

        # Multiple inputs -- align, upsample, and average
        for i, extra in enumerate(fields[1:], start=1):
            img = np.asarray(extra.data, dtype=np.float64)

            # Find sub-pixel shift relative to reference
            dy, dx = _find_subpixel_shift(ref, img)

            alignment.append({"quantity": f"Frame {i + 1} shift X (px)", "value": float(dx), "unit": "px"})
            alignment.append({"quantity": f"Frame {i + 1} shift Y (px)", "value": float(dy), "unit": "px"})
            alignment.append({"quantity": f"Frame {i + 1} shift X", "value": float(dx) * field1.dx, "unit": field1.si_unit_xy})
            alignment.append({"quantity": f"Frame {i + 1} shift Y", "value": float(dy) * field1.dy, "unit": field1.si_unit_xy})

            # Shift in high-res coordinates
            shifted = ndimage_shift(img.astype(np.float64), (-dy, -dx), order=3)
            upsampled = ndimage_zoom(shifted, upscale, order=3)

            # Accumulate
            high_res += upsampled
            weight += 1.0

        high_res /= weight

        emit_table(alignment)
        return (field1.replace(
            data=high_res,
            xreal=field1.xreal,
            yreal=field1.yreal,
        ), alignment)
