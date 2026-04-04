"""Perspective correction — fix perspective distortion using a projective transform."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Perspective Correction")
class PerspectiveCorrection:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "top_left_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "top_left_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "top_right_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "top_right_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "bottom_left_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "bottom_left_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "bottom_right_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "bottom_right_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fix perspective distortion by specifying corner offsets. Each corner "
        "can be shifted by a fractional amount (relative to image size) to "
        "define the distorted quadrilateral. The image is then warped back to "
        "a rectangle."
    )

    def process(self, field: DataField,
                top_left_x: float, top_left_y: float,
                top_right_x: float, top_right_y: float,
                bottom_left_x: float, bottom_left_y: float,
                bottom_right_x: float, bottom_right_y: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Source corners (distorted) as fractional offsets from ideal corners
        src = np.array([
            [top_left_y * yres, top_left_x * xres],
            [top_right_y * yres, top_right_x * xres + (xres - 1)],
            [(1 + bottom_left_y) * yres - 1, bottom_left_x * xres],
            [(1 + bottom_right_y) * yres - 1, bottom_right_x * xres + (xres - 1)],
        ], dtype=np.float64)

        # Destination corners (ideal rectangle)
        dst = np.array([
            [0, 0],
            [0, xres - 1],
            [yres - 1, 0],
            [yres - 1, xres - 1],
        ], dtype=np.float64)

        # Solve for perspective transform matrix (3x3)
        H = _solve_perspective(src, dst)

        # Apply inverse warp
        yy, xx = np.mgrid[:yres, :xres]
        coords = np.stack([yy.ravel(), xx.ravel(), np.ones(yres * xres)])
        src_coords = H @ coords
        src_coords /= src_coords[2:3, :]
        sy = src_coords[0].reshape(yres, xres)
        sx = src_coords[1].reshape(yres, xres)

        result = map_coordinates(data, [sy, sx], order=1, mode='nearest')
        return (field.replace(data=result),)


def _solve_perspective(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Solve for 3x3 perspective matrix mapping dst -> src (for inverse warp)."""
    n = len(src)
    A = np.zeros((2 * n, 8))
    b = np.zeros(2 * n)
    for i in range(n):
        dy, dx = dst[i]
        sy, sx = src[i]
        A[2 * i] = [dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy]
        A[2 * i + 1] = [0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy]
        b[2 * i] = sx
        b[2 * i + 1] = sy
    h, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    H = np.array([[h[0], h[1], h[2]],
                   [h[3], h[4], h[5]],
                   [h[6], h[7], 1.0]])
    return H
