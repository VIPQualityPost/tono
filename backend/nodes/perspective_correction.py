"""Perspective correction — fix perspective distortion using a projective transform."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField, datafield_to_uint8, encode_preview
from backend.execution_context import emit_overlay


@register_node(display_name="Perspective Correction")
class PerspectiveCorrection:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "top_left_x": ("FLOAT", {"default": 0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "top_left_y": ("FLOAT", {"default": 0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "top_right_x": ("FLOAT", {"default": -0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "top_right_y": ("FLOAT", {"default": 0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "bottom_left_x": ("FLOAT", {"default": 0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "bottom_left_y": ("FLOAT", {"default": -0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "bottom_right_x": ("FLOAT", {"default": -0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "bottom_right_y": ("FLOAT", {"default": -0.1, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
            },
            "optional": {
                "top_left": ("COORD",),
                "top_right": ("COORD",),
                "bottom_left": ("COORD",),
                "bottom_right": ("COORD",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fix perspective distortion by dragging corner handles. Each corner "
        "offset defines a distorted quadrilateral that is warped back to "
        "a rectangle."
    )

    KEYWORDS = ("keystone", "homography", "projective", "warp", "quadrilateral", "distortion")

    def process(self, field: DataField,
                top_left_x: float, top_left_y: float,
                top_right_x: float, top_right_y: float,
                bottom_left_x: float, bottom_left_y: float,
                bottom_right_x: float, bottom_right_y: float,
                top_left: tuple[float, float] | None = None,
                top_right: tuple[float, float] | None = None,
                bottom_left: tuple[float, float] | None = None,
                bottom_right: tuple[float, float] | None = None) -> tuple:
        if top_left is not None:
            top_left_x, top_left_y = float(top_left[0]), float(top_left[1])
        if top_right is not None:
            top_right_x, top_right_y = float(top_right[0]), float(top_right[1])
        if bottom_left is not None:
            bottom_left_x, bottom_left_y = float(bottom_left[0]), float(bottom_left[1])
        if bottom_right is not None:
            bottom_right_x, bottom_right_y = float(bottom_right[0]), float(bottom_right[1])

        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        src = np.array([
            [top_left_y * yres, top_left_x * xres],
            [top_right_y * yres, top_right_x * xres + (xres - 1)],
            [(1 + bottom_left_y) * yres - 1, bottom_left_x * xres],
            [(1 + bottom_right_y) * yres - 1, bottom_right_x * xres + (xres - 1)],
        ], dtype=np.float64)

        dst = np.array([
            [0, 0],
            [0, xres - 1],
            [yres - 1, 0],
            [yres - 1, xres - 1],
        ], dtype=np.float64)

        H = _solve_perspective(src, dst)

        yy, xx = np.mgrid[:yres, :xres]
        coords = np.stack([xx.ravel(), yy.ravel(), np.ones(yres * xres)])
        src_coords = H @ coords
        src_coords /= src_coords[2:3, :]
        sx = src_coords[0].reshape(yres, xres)
        sy = src_coords[1].reshape(yres, xres)

        result = map_coordinates(data, [sy, sx], order=1, mode='nearest')
        corrected = field.replace(data=result)

        source_rgb = datafield_to_uint8(field, field.colormap)
        corrected_rgb = datafield_to_uint8(corrected, corrected.colormap)

        corners = [
            {"x": float(top_left_x), "y": float(top_left_y)},
            {"x": float(top_right_x), "y": float(top_right_y)},
            {"x": float(bottom_left_x), "y": float(bottom_left_y)},
            {"x": float(bottom_right_x), "y": float(bottom_right_y)},
        ]

        emit_overlay({
            "kind": "perspective",
            "section_title": "Perspective",
            "image": encode_preview(source_rgb),
            "corrected_image": encode_preview(corrected_rgb),
            "corners": corners,
        })

        return (corrected,)


def _solve_perspective(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Solve for 3x3 perspective matrix mapping dst -> src (for inverse warp).

    Coordinates are (col, row) — the matrix is applied to [col, row, 1] vectors.
    """
    n = len(src)
    A = np.zeros((2 * n, 8))
    b = np.zeros(2 * n)
    for i in range(n):
        dr, dc = dst[i]    # dest row, col
        sr, sc = src[i]    # src row, col
        A[2 * i]     = [dc, dr, 1, 0,  0,  0, -sc * dc, -sc * dr]
        A[2 * i + 1] = [0,  0,  0, dc, dr, 1, -sr * dc, -sr * dr]
        b[2 * i] = sc
        b[2 * i + 1] = sr
    h, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    H = np.array([[h[0], h[1], h[2]],
                   [h[3], h[4], h[5]],
                   [h[6], h[7], 1.0]])
    return H
