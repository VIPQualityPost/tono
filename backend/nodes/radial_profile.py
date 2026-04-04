from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, LineData


@register_node(display_name="Radial Profile")
class RadialProfile:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "cx": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "cy": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "n_bins": ("INT", {"default": 128, "min": 4, "max": 4096, "step": 1}),
            }
        }

    OUTPUTS = (
        ('LINE', 'profile'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the azimuthally averaged radial profile from a centre point. "
        "cx/cy give the centre as a fraction of the field width/height (0.5 = centre). "
        "Output x-axis is radius in physical xy units. "
    )

    KEYWORDS = ("azimuthal average", "ring average", "circular", "isotropic")

    def process(self, field: DataField, cx: float, cy: float, n_bins: int) -> tuple:
        yres, xres = field.data.shape

        # Centre in physical coordinates (matches Gwyddion: xc = cx*xreal + xoff)
        xc_phys = cx * field.xreal + field.xoff
        yc_phys = cy * field.yreal + field.yoff

        # Pixel-centre physical coordinates
        xs = (np.arange(xres) + 0.5) * field.dx + field.xoff
        ys = (np.arange(yres) + 0.5) * field.dy + field.yoff
        gx, gy = np.meshgrid(xs, ys)

        r = np.hypot(gx - xc_phys, gy - yc_phys).ravel()
        values = field.data.ravel()

        # Maximum radius — farthest pixel from centre
        r_max = float(r.max())
        if r_max == 0.0:
            r_max = max(field.dx, field.dy)

        # Bin by radius — matches Gwyddion's lineres-bin approach
        bin_edges = np.linspace(0.0, r_max, n_bins + 1)
        idx = np.clip(
            np.floor(n_bins * r / r_max).astype(np.intp), 0, n_bins - 1
        )

        sums = np.zeros(n_bins)
        counts = np.zeros(n_bins, dtype=np.intp)
        np.add.at(sums, idx, values)
        np.add.at(counts, idx, 1)

        with np.errstate(invalid="ignore"):
            profile = np.where(counts > 0, sums / counts, np.nan)

        centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

        return (LineData(
            data=profile,
            x_axis=centers,
            x_unit=field.si_unit_xy,
            y_unit=field.si_unit_z,
        ),)
