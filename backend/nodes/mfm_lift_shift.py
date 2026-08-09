"""MFM Lift Shift — rescale an MFM field to a different lift height."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


def _mfm_shift_z(data: np.ndarray, xreal: float, yreal: float, zdiff: float) -> np.ndarray:
    """Shift a field to a different lift height via the FFT transfer function.

    Each spatial frequency |k| (cycles per metre) is attenuated by the
    exponential transfer function exp(-2*pi*|k|*zdiff), which corresponds to
    propagating the field away from (zdiff > 0) or towards (zdiff < 0) the
    surface.  The frequency magnitudes use the unshifted FFT arrangement,
    i.e. |k| = sqrt((j/xreal)^2 + (i/yreal)^2).
    """
    yres, xres = data.shape
    kx = np.fft.fftfreq(xres, d=xreal / xres)
    ky = np.fft.fftfreq(yres, d=yreal / yres)
    KX, KY = np.meshgrid(kx, ky)
    K = np.sqrt(KX * KX + KY * KY)
    ztf = np.exp(-2.0 * np.pi * K * zdiff)
    return np.real(np.fft.ifft2(np.fft.fft2(data) * ztf))


@register_node(display_name="MFM Lift Shift")
class MFMLiftShift:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shift_z": ("FLOAT", {
                    "default": 10e-9, "min": -1e-6, "max": 1e-6, "step": 1e-9,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'shifted'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    CATEGORY = "SPM"

    DESCRIPTION = (
        "Shifts a magnetic field image to a different lift height above the "
        "surface using the FFT-based transfer function exp(-2*pi*|k|*dz). A "
        "positive shift moves away from the surface and blurs the data; a "
        "negative shift sharpens it (the result then grows exponentially and "
        "is generally not very useful)."
    )

    KEYWORDS = ("magnetic", "mfM", "lift", "shift", "height", "transfer function", "fft")

    def process(self, field: DataField, shift_z: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        shifted = _mfm_shift_z(data, field.xreal, field.yreal, float(shift_z))

        table = RecordTable([
            {"quantity": "Effective lift shift", "value": float(shift_z), "unit": "m"},
        ])
        emit_table(table)

        return (field.replace(data=shifted), table)
