from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Spot Removal")
class SpotRemoval:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["laplace", "mean", "zero"], {"default": "laplace"}),
                "max_iter": ("INT", {"default": 100, "min": 1, "max": 2000, "step": 1}),
            },
            "optional": {
                "mask": ("IMAGE", {"label": "defects"}),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fill defect pixels (hot pixels, dropouts, scan artifacts) by interpolation. "
        "The mask defines defect locations. Laplace method solves the 2D Laplace equation "
        "for smooth inpainting."
    )

    KEYWORDS = ("defect", "hot pixel", "dropout", "inpaint", "fill", "despeckle", "artifact")

    def process(
        self,
        field: DataField,
        method: str,
        max_iter: int,
        mask: np.ndarray | None = None,
    ) -> tuple:
        if mask is None:
            return (field,)

        mask_array = np.asarray(mask)
        # Reshape mask to match field shape if it has extra dimensions (e.g. HxWx1)
        if mask_array.ndim == 3:
            mask_array = mask_array[:, :, 0]
        if mask_array.shape != field.data.shape:
            raise ValueError(
                f"Mask shape {mask_array.shape} does not match field shape {field.data.shape}."
            )

        defect = mask_array > 0

        if not np.any(defect):
            return (field,)

        data = np.asarray(field.data, dtype=np.float64)

        if method == "zero":
            result = data.copy()
            result[defect] = 0.0
            return (field.replace(data=result),)

        if method == "mean":
            result = _mean_fill(data, defect)
            return (field.replace(data=result),)

        # method == "laplace"
        result = _laplace_fill(data, defect, int(max_iter))
        return (field.replace(data=result),)


def _mean_fill(data: np.ndarray, defect: np.ndarray) -> np.ndarray:
    """Fill defect pixels with the mean of non-defect neighbours in a 3x3 window."""
    result = data.copy()
    yres, xres = data.shape

    # Global fallback: mean of all non-defect pixels
    non_defect_vals = data[~defect]
    global_mean = float(non_defect_vals.mean()) if non_defect_vals.size > 0 else 0.0

    defect_coords = np.argwhere(defect)
    for y, x in defect_coords:
        y0 = max(y - 1, 0)
        y1 = min(y + 2, yres)
        x0 = max(x - 1, 0)
        x1 = min(x + 2, xres)

        neighbourhood_data = data[y0:y1, x0:x1]
        neighbourhood_defect = defect[y0:y1, x0:x1]
        good = neighbourhood_data[~neighbourhood_defect]

        if good.size > 0:
            result[y, x] = float(good.mean())
        else:
            result[y, x] = global_mean

    return result


def _laplace_fill(data: np.ndarray, defect: np.ndarray, max_iter: int) -> np.ndarray:
    """Iterative Laplace solver: set defect pixels to neighbour average each iteration."""
    non_defect_vals = data[~defect]
    init_val = float(non_defect_vals.mean()) if non_defect_vals.size > 0 else 0.0

    result = data.copy()
    result[defect] = init_val

    for _ in range(max_iter):
        # Compute neighbour averages via rolled arrays
        neighbour_sum = (
            np.roll(result, -1, axis=0)
            + np.roll(result,  1, axis=0)
            + np.roll(result, -1, axis=1)
            + np.roll(result,  1, axis=1)
        )
        new_vals = neighbour_sum / 4.0
        result[defect] = new_vals[defect]

    return result
