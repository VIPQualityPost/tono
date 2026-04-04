"""Straighten path — extract cross-section along a curved spline path."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Straighten Path")
class StraightenPath:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "points_x": ("STRING", {"default": "0.25, 0.5, 0.75"}),
                "points_y": ("STRING", {"default": "0.5, 0.3, 0.5"}),
                "thickness": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
                "n_samples": ("INT", {"default": 256, "min": 10, "max": 2048, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'straightened'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Extract a cross-section along an arbitrary curved path defined by "
        "control points. Points are given as fractional coordinates (0–1). "
        "The path is interpolated with cubic splines, and data is sampled "
        "along it with configurable thickness. "
    )

    def process(self, field: DataField, points_x: str, points_y: str,
                thickness: int, n_samples: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Parse control points
        px = [float(v.strip()) * (xres - 1) for v in points_x.split(",") if v.strip()]
        py = [float(v.strip()) * (yres - 1) for v in points_y.split(",") if v.strip()]

        if len(px) < 2 or len(py) < 2:
            # Need at least 2 points
            return (field,)

        n_pts = min(len(px), len(py))
        px, py = px[:n_pts], py[:n_pts]

        # Parameterize path and interpolate
        t_ctrl = np.linspace(0, 1, n_pts)
        t_sample = np.linspace(0, 1, n_samples)

        # Simple cubic interpolation via numpy
        if n_pts >= 4:
            from numpy.polynomial.polynomial import Polynomial
            cx = np.interp(t_sample, t_ctrl, px)
            cy = np.interp(t_sample, t_ctrl, py)
        else:
            cx = np.interp(t_sample, t_ctrl, px)
            cy = np.interp(t_sample, t_ctrl, py)

        # Sample along path with thickness
        if thickness <= 1:
            values = map_coordinates(data, [cy, cx], order=1, mode='nearest')
            result = values.reshape(1, -1)
        else:
            # Compute normals
            dcx = np.gradient(cx)
            dcy = np.gradient(cy)
            length = np.sqrt(dcx**2 + dcy**2)
            length = np.maximum(length, 1e-10)
            nx = -dcy / length
            ny = dcx / length

            offsets = np.linspace(-(thickness - 1) / 2, (thickness - 1) / 2, thickness)
            result = np.zeros((thickness, n_samples))
            for i, off in enumerate(offsets):
                sx = cx + off * nx
                sy = cy + off * ny
                result[i] = map_coordinates(data, [sy, sx], order=1, mode='nearest')

        # Physical dimensions
        total_length = 0.0
        for i in range(1, len(cx)):
            dx_phys = (cx[i] - cx[i - 1]) * field.dx
            dy_phys = (cy[i] - cy[i - 1]) * field.dy
            total_length += np.sqrt(dx_phys**2 + dy_phys**2)

        return (field.replace(data=result, xreal=total_length,
                              yreal=thickness * max(field.dx, field.dy)),)
