"""Affine correction — fix geometric distortions from scanner nonlinearity."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import affine_transform

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Affine Correction")
class AffineCorrection:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shear_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "shear_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "scale_x": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01}),
                "scale_y": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01}),
                "angle": ("FLOAT", {"default": 0.0, "min": -45.0, "max": 45.0, "step": 0.1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply an affine correction to fix geometric distortions from scanner "
        "nonlinearity. Parameters specify shear, scale, and rotation corrections. "
        "The transform is applied about the centre of the field. "
    )

    KEYWORDS = ("shear", "scale", "distortion", "warp")

    def process(
        self,
        field: DataField,
        shear_x: float,
        shear_y: float,
        scale_x: float,
        scale_y: float,
        angle: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        cy, cx = yres / 2.0, xres / 2.0

        theta = np.radians(angle)
        cos_t, sin_t = np.cos(theta), np.sin(theta)

        # Build the correction matrix: Scale * Shear * Rotation
        rotation = np.array([[cos_t, -sin_t], [sin_t, cos_t]])
        shear = np.array([[1.0, shear_x], [shear_y, 1.0]])
        scale = np.array([[1.0 / scale_x, 0.0], [0.0, 1.0 / scale_y]])

        matrix = scale @ shear @ rotation

        # Offset so the transform is centred
        offset = np.array([cy, cx]) - matrix @ np.array([cy, cx])

        corrected = affine_transform(data, matrix, offset=offset, order=3, mode="reflect")
        return (field.replace(data=corrected),)
