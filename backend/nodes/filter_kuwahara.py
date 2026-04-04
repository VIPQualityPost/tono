from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


def _kuwahara_pass(data: np.ndarray) -> np.ndarray:
    """Single pass of the 5x5 Kuwahara filter.

    Divides a 5x5 neighbourhood around each pixel into four overlapping 3x3
    quadrants (TL, TR, BL, BR), computes the mean and variance of each quadrant,
    and replaces the centre pixel with the mean of the quadrant that has the
    smallest variance. Boundary pixels are handled by reflecting the image.
    """
    # Pad with reflect so every pixel has a full 5x5 neighbourhood.
    padded = np.pad(data, pad_width=2, mode="reflect")

    rows, cols = data.shape

    # For each of the four 3x3 quadrant offsets we need the per-pixel mean and
    # variance.  The quadrant window positions (relative to the padded array)
    # for a centre pixel at (r+2, c+2) are:
    #   TL : rows r..r+2,  cols c..c+2    →  offset (0,0) in padded
    #   TR : rows r..r+2,  cols c+2..c+4  →  offset (0,2)
    #   BL : rows r+2..r+4, cols c..c+2   →  offset (2,0)
    #   BR : rows r+2..r+4, cols c+2..c+4 →  offset (2,2)
    # Each window is 3×3 = 9 pixels.

    quadrant_offsets = [(0, 0), (0, 2), (2, 0), (2, 2)]
    n = 9  # 3×3 quadrant

    # Accumulate sum and sum-of-squares for each quadrant using a simple nested
    # index loop over the 3×3 window positions.
    quad_sum = np.zeros((4, rows, cols), dtype=np.float64)
    quad_sum2 = np.zeros((4, rows, cols), dtype=np.float64)

    for qi, (dr0, dc0) in enumerate(quadrant_offsets):
        for drow in range(3):
            for dcol in range(3):
                patch = padded[dr0 + drow: dr0 + drow + rows,
                               dc0 + dcol: dc0 + dcol + cols]
                quad_sum[qi] += patch
                quad_sum2[qi] += patch * patch

    quad_mean = quad_sum / n
    # var = E[x^2] - (E[x])^2, clamped to 0 to avoid floating-point negatives.
    quad_var = np.maximum(quad_sum2 / n - quad_mean * quad_mean, 0.0)

    # Select the quadrant index with minimum variance for each pixel.
    best_qi = np.argmin(quad_var, axis=0)  # shape (rows, cols)

    # Gather the mean from the winning quadrant.
    result = np.choose(best_qi, quad_mean)
    return result.astype(np.float64)


@register_node(display_name="Kuwahara Filter")
class KuwaharaFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "iterations": ("INT", {"default": 1, "min": 1, "max": 20}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filtered'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        """
        Edge-preserving smoothing using Kuwahara's minimum-variance quadrant method.
        "Unlike Gaussian blur, sharp boundaries are preserved. 
        """
    )

    def process(self, field: DataField, iterations: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        iterations = max(1, int(iterations))
        for _ in range(iterations):
            data = _kuwahara_pass(data)
        return (field.replace(data=data),)
