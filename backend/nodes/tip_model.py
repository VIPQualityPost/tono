from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Tip Model")
class TipModel:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shape": (["parabola", "cone", "sphere"], {"default": "parabola"}),
                "radius": ("FLOAT", {
                    "default": 10e-9, "min": 1e-10, "max": 1e-6, "step": 1e-10,
                }),
                "half_angle": ("FLOAT", {
                    "default": 20.0, "min": 1.0, "max": 89.0, "step": 0.5,
                }),
                "n_pixels": ("INT", {"default": 65, "min": 3, "max": 511, "step": 2}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'tip'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Generate a synthetic AFM tip model DATA_FIELD. "
        "The input field sets the pixel size for the tip. "
        "The apex (centre pixel) is the maximum value; edges are shifted to zero. "
        "Shapes: parabola — paraboloid with apex radius R; "
        "cone — sphere-capped cone (radius R, half_angle from tip axis in degrees); "
        "sphere — ball-on-stick (sphere cap only). "
    )

    KEYWORDS = ("apex", "parabola", "cone", "sphere", "synthetic", "probe", "cantilever")

    def process(
        self,
        field: DataField,
        shape: str,
        radius: float,
        half_angle: float,
        n_pixels: int,
    ) -> tuple:
        pixel_size = (field.dx + field.dy) * 0.5

        # Ensure odd size so the centre pixel is well-defined
        n = n_pixels if n_pixels % 2 == 1 else n_pixels + 1
        ci = n // 2

        # Physical offsets from the centre pixel
        offsets = (np.arange(n) - ci) * pixel_size
        gx, gy = np.meshgrid(offsets, offsets)
        r2 = gx**2 + gy**2
        r = np.sqrt(r2)

        if shape == "parabola":
            # Parabola shape: a = 1/(2R), z0 = 2a·x_half²
            # z[y,x] = z0 - a·r²  →  min at corners is exactly 0
            a = 0.5 / radius
            x_half = ci * pixel_size        # half-width in physical units
            z0 = 2.0 * a * x_half**2
            data = z0 - a * r2
            data -= data.min()              # shift so min = 0

        elif shape == "cone":
            # Cone shape:
            #   angle = half-angle from horizontal = π/2 - half_angle_from_axis
            #   z0 = R/sin(angle)
            #   r_cross² = (R·cos(angle))²
            #   inner (r² < r_cross²): z = sqrt(R² - r²)   ← spherical cap
            #   outer:                  z = z0 - r/tan(angle)
            angle = np.radians(90.0 - half_angle)   # slope from horizontal
            z0 = radius / np.sin(angle)
            br2 = (radius * np.cos(angle))**2
            ta = 1.0 / np.tan(angle)
            inner = np.sqrt(np.maximum(0.0, radius**2 - r2))
            outer = z0 - ta * r
            data = np.where(r2 < br2, inner, outer)
            data -= data.min()

        elif shape == "sphere":
            # Sphere shape: cone with near-vertical sides (angle ≈ 0 from horizontal)
            angle = 1e-5   # radians — essentially vertical cone
            z0 = radius / np.sin(angle)
            br2 = (radius * np.cos(angle))**2
            ta = 1.0 / np.tan(angle)
            inner = np.sqrt(np.maximum(0.0, radius**2 - r2))
            outer = z0 - ta * r
            data = np.where(r2 < br2, inner, outer)
            data -= data.min()

        else:
            raise ValueError(f"Unknown tip shape {shape!r}. Choose: parabola, cone, sphere.")

        xreal = n * pixel_size
        tip_field = DataField(
            data=data,
            xreal=xreal,
            yreal=xreal,
            si_unit_xy=field.si_unit_xy,
            si_unit_z=field.si_unit_z,
        )
        return (tip_field,)
