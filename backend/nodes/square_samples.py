from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Square Samples")
class SquareSamples:
    """Resample a DATA_FIELD so lateral pixel sizes dx == dy (Gwyddion `square_samples`)."""

    CATEGORY = "Geometry"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "interpolation": (["linear", "cubic", "nearest"], {"default": "cubic"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Resample a DATA_FIELD with a non-1:1 aspect ratio so that the lateral "
        "pixel sizes dx and dy become equal (square samples), while physical extents "
        "are preserved. The axis sampled more coarsely gains pixels to match the "
        "sampling density of the other axis. If the sampling densities already "
        "match, the field is returned unchanged."
    )

    KEYWORDS = ("square", "resample", "aspect ratio", "dx", "dy", "pixel size")

    _ORDERS = {"nearest": 0, "linear": 1, "cubic": 3}

    def process(self, field: DataField, interpolation: str) -> tuple:
        if interpolation not in self._ORDERS:
            raise ValueError(
                f"Unknown interpolation {interpolation!r}. "
                f"Choose from: {list(self._ORDERS)}"
            )

        xres, yres = field.xres, field.yres
        xreal, yreal = field.xreal, field.yreal
        # Sampling density (samples per metre)
        qx = xres / xreal if xreal else 0.0
        qy = yres / yreal if yreal else 0.0

        # Gwyddion square_samples(): resample the deficient axis unless the
        # densities are equal within 1/sqrt(xres^2 + yres^2).
        if abs(np.log(qx / qy)) > 1.0 / np.hypot(xres, yres):
            if qx < qy:
                new_xres = max(int(np.floor(xreal * qy + 0.5)), 1)
                new_yres = yres
            else:
                new_yres = max(int(np.floor(yreal * qx + 0.5)), 1)
                new_xres = xres

            from scipy.ndimage import zoom

            result = zoom(
                field.data,
                (new_yres / yres, new_xres / xres),
                order=self._ORDERS[interpolation],
            )
            # zoom can be off by one pixel; trim/pad to the exact target size
            if result.shape != (new_yres, new_xres):
                result = _fit_shape(result, new_yres, new_xres)
        else:
            # Ratios are equal — duplicate the field unchanged
            result = field.data.copy()

        return (field.replace(data=np.asarray(result, dtype=np.float64)),)


def _fit_shape(arr: np.ndarray, new_yres: int, new_xres: int) -> np.ndarray:
    """Trim or edge-pad *arr* to exactly (new_yres, new_xres)."""
    cy, cx = arr.shape
    if cy > new_yres:
        arr = arr[:new_yres, :]
    elif cy < new_yres:
        arr = np.pad(arr, ((0, new_yres - cy), (0, 0)), mode="edge")
    if cx > new_xres:
        arr = arr[:, :new_xres]
    elif cx < new_xres:
        arr = np.pad(arr, ((0, 0), (0, new_xres - cx)), mode="edge")
    return arr
