from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node
from backend.nodes.helpers import _square_unit


def _product_unit(unit_a: str, unit_b: str) -> str:
    """Value units of a convolution sum: product of the two inputs' units.

    The result's value unit is the product of the field and kernel value units.
    """
    ua = str(unit_a or "").strip()
    ub = str(unit_b or "").strip()
    if not ua:
        return ub
    if not ub:
        return ua
    if ua == ub:
        return _square_unit(ua)
    return f"{ua}·{ub}"


@register_node(display_name="Convolve")
class ConvolveTwoImages:
    CATEGORY = "Geometry"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "mode": (["full", "same", "valid"], {"default": "same"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'convolved'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Convolve two images. The result value at each pixel is the sum of the "
        "product of field_a with the reversed field_b kernel, computed with FFT "
        "convolution, with the kernel centred on the output pixel (zero exterior). "
        "Mode selects the output "
        "extent: full (Na+Nb-1), same (field_a size) or valid (overlap only, "
        "requires field_b smaller than field_a)."
    )

    KEYWORDS = ("convolve", "convolution", "kernel", "filter", "blur")

    def process(self, field_a: DataField, field_b: DataField, mode: str) -> tuple:
        from scipy.signal import fftconvolve

        a = np.asarray(field_a.data, dtype=np.float64)
        b = np.asarray(field_b.data, dtype=np.float64)
        if mode == "valid":
            if b.shape[0] > a.shape[0] or b.shape[1] > a.shape[1]:
                raise ValueError(
                    f"field_b ({b.shape[1]}x{b.shape[0]}) is larger than field_a "
                    f"({a.shape[1]}x{a.shape[0]}); valid mode needs field_b to fit inside field_a"
                )

        if mode == "same":
            # Gwyddion convolves with the kernel centre at kx//2, ky//2 (for
            # even kernels this sits 0.5 px towards lower indices, which scipy's
            # 'same' mode does not reproduce).  Slice the zero-exterior full
            # convolution exactly like gwy_data_field_area_ext_convolve().
            na, ma = a.shape
            ky, kx = b.shape
            full = fftconvolve(a, b, mode="full")
            out = full[ky // 2:ky // 2 + na, kx // 2:kx // 2 + ma]
            return (field_a.replace(data=out, si_unit_z=_product_unit(field_a.si_unit_z, field_b.si_unit_z)),)

        out = fftconvolve(a, b, mode=mode)
        # full/valid: pixel size is preserved from field_a, the physical extents
        # scale proportionally with the output resolution (same convention as the
        # Cross-Correlate node).
        na, ma = a.shape
        out_y, out_x = out.shape
        new_yreal = field_a.yreal * out_y / na if na else field_a.yreal
        new_xreal = field_a.xreal * out_x / ma if ma else field_a.xreal
        return (
            field_a.replace(
                data=out,
                xreal=new_xreal,
                yreal=new_yreal,
                si_unit_z=_product_unit(field_a.si_unit_z, field_b.si_unit_z),
            ),
        )
