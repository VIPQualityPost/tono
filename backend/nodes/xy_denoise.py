from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node

# G_MINDOUBLE used by Gwyddion as the phase-normalisation floor.
_TINY = np.finfo(np.float64).tiny


@register_node(display_name="XY Denoise")
class XYDenoise:
    CATEGORY = "Geometry"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_x": ("DATA_FIELD",),
                "field_y": ("DATA_FIELD",),
                "do_average": ("BOOLEAN", {"default": True}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'denoised'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Denoise a measurement acquired as two orthogonal scans (e.g. horizontal "
        "and vertical fast-scan directions), as in Gwyddion's XY Denoise. The two "
        "fields are Fourier transformed; at every frequency the shared modulus is "
        "taken as the smaller of the two moduli and the phase comes from the "
        "horizontal scan (or the average of both phases when averaging is enabled). "
        "The inverse transform keeps only the component the two scans agree on, "
        "suppressing scan-direction noise and artefacts."
    )

    KEYWORDS = ("xy denoise", "denoise", "orthogonal", "scan", "fourier", "phase", "noise")

    def process(
        self,
        field_x: DataField,
        field_y: DataField,
        do_average: bool,
    ) -> tuple:
        x = np.asarray(field_x.data, dtype=np.float64)
        y = np.asarray(field_y.data, dtype=np.float64)
        if x.shape != y.shape:
            raise ValueError(
                f"Both scans must have the same resolution: field_x {x.shape}, "
                f"field_y {y.shape}"
            )
        if field_x.si_unit_xy != field_y.si_unit_xy or field_x.si_unit_z != field_y.si_unit_z:
            raise ValueError(
                "Both scans must use the same units "
                f"(field_x: xy={field_x.si_unit_xy}, z={field_x.si_unit_z}; "
                f"field_y: xy={field_y.si_unit_xy}, z={field_y.si_unit_z})"
            )
        if not (np.isclose(field_x.xreal, field_y.xreal) and np.isclose(field_x.yreal, field_y.yreal)):
            raise ValueError(
                "Both scans must cover the same physical area "
                f"(field_x: {field_x.xreal}x{field_x.yreal}, "
                f"field_y: {field_y.xreal}x{field_y.yreal})"
            )

        fx = np.fft.fft2(x)
        fy = np.fft.fft2(y)

        # Phase of each scan, with Gwyddion's fmax(modulus, G_MINDOUBLE) floor.
        xmodulus = np.abs(fx)
        ymodulus = np.abs(fy)
        cosxphase = fx.real / np.maximum(xmodulus, _TINY)
        sinxphase = fx.imag / np.maximum(xmodulus, _TINY)
        if do_average:
            cosxphase = 0.5 * (cosxphase + fy.real / np.maximum(ymodulus, _TINY))
            sinxphase = 0.5 * (sinxphase + fy.imag / np.maximum(ymodulus, _TINY))

        # Shared modulus: the smaller amplitude of the two scans.
        modulus = np.minimum(xmodulus, ymodulus)

        fout = modulus * (cosxphase + 1j * sinxphase)
        result = np.fft.ifft2(fout).real

        return (field_x.replace(data=result),)
