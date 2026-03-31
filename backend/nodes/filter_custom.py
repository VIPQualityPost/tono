from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.execution_context import emit_warning

_DEFAULT_KERNEL = "0 -1 0\n-1 5 -1\n0 -1 0"
_MAX_KERNEL_DIM = 51


def _parse_kernel(kernel_str: str) -> np.ndarray | None:
    """Parse a multi-line kernel string into a 2-D float64 array.

    Returns *None* and issues a warning via emit_warning if the string is
    invalid.  The returned array is always at least 1×1 and at most
    _MAX_KERNEL_DIM × _MAX_KERNEL_DIM.
    """
    lines = [ln for ln in kernel_str.splitlines() if ln.strip()]
    if not lines:
        emit_warning("Custom Convolution: kernel string is empty. Using identity.")
        return None

    rows = []
    for ln in lines:
        try:
            row = [float(v) for v in ln.split()]
        except ValueError:
            emit_warning(
                f"Custom Convolution: could not parse kernel row {ln!r}. "
                "Input returned unchanged."
            )
            return None
        if not row:
            continue
        rows.append(row)

    if not rows:
        emit_warning("Custom Convolution: kernel has no valid rows. Input returned unchanged.")
        return None

    # All rows must have the same length.
    ncols = len(rows[0])
    for i, row in enumerate(rows):
        if len(row) != ncols:
            emit_warning(
                f"Custom Convolution: row {i} has {len(row)} values but row 0 has {ncols}. "
                "All rows must be the same length. Input returned unchanged."
            )
            return None

    arr = np.array(rows, dtype=np.float64)

    if arr.ndim != 2 or arr.size == 0:
        emit_warning("Custom Convolution: kernel is empty after parsing. Input returned unchanged.")
        return None

    nrows, ncols = arr.shape
    if nrows > _MAX_KERNEL_DIM or ncols > _MAX_KERNEL_DIM:
        emit_warning(
            f"Custom Convolution: kernel size {nrows}×{ncols} exceeds maximum "
            f"{_MAX_KERNEL_DIM}×{_MAX_KERNEL_DIM}. Input returned unchanged."
        )
        return None

    if not np.all(np.isfinite(arr)):
        emit_warning("Custom Convolution: kernel contains non-finite values. Input returned unchanged.")
        return None

    return arr


@register_node(display_name="Custom Convolution")
class CustomConvolution:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "kernel": ("STRING", {
                    "multiline": True,
                    "default": _DEFAULT_KERNEL,
                    "placeholder": "kernel rows, space-separated",
                }),
                "normalize": ("BOOLEAN", {"default": True}),
                "boundary": (["reflect", "nearest", "wrap"], {"default": "reflect"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply a user-defined convolution kernel. "
        "Enter rows of space-separated numbers. "
        "Example sharpen: '0 -1 0 / -1 5 -1 / 0 -1 0' (use newlines, not slashes). "
        "Equivalent to Gwyddion convolution_filter.c."
    )

    def process(
        self,
        field: DataField,
        kernel: str,
        normalize: bool,
        boundary: str,
    ) -> tuple:
        from scipy.ndimage import convolve

        kernel_arr = _parse_kernel(kernel)
        if kernel_arr is None:
            # Fallback: return input unchanged.
            return (field.replace(data=field.data.copy()),)

        data = np.asarray(field.data, dtype=np.float64)

        # scipy.ndimage.convolve boundary mode names match our choices directly.
        result = convolve(data, kernel_arr, mode=boundary)

        if normalize:
            abs_sum = float(np.sum(np.abs(kernel_arr)))
            if abs_sum > 0.0:
                result = result / abs_sum

        return (field.replace(data=result),)
