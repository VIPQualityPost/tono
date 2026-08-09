from __future__ import annotations

import numpy as np

from backend.data_types import (
    DataField,
    LineData,
    encode_preview,
    render_datafield_preview,
)
from backend.execution_context import emit_overlay
from backend.node_registry import register_node


@register_node(display_name="Radial Profile")
class RadialProfile:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_bins": ("INT", {"default": 128, "min": 4, "max": 4096, "step": 1}),
                "cx": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "cy": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "ex": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "ey": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
            }
        }

    OUTPUTS = (
        ('LINE', 'profile'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute an azimuthally averaged profile around a center point. "
        "At each radius, every pixel in the full 360° ring is averaged together, "
        "so the profile is direction-independent — there is no clockwise/counter-clockwise "
        "traversal and no start/end point along the ring. "
        "Drag the center marker on the preview to reposition the profile, "
        "or drag either end marker (both just set the outer radius) to change the extent. "
        "Output x-axis is radius in physical xy units."
    )

    KEYWORDS = ("azimuthal average", "ring average", "circular", "isotropic")

    def process(
        self,
        field: DataField,
        n_bins: int,
        cx: float,
        cy: float,
        ex: float,
        ey: float,
    ) -> tuple:
        yres, xres = field.data.shape

        cx = float(np.clip(cx, 0.0, 1.0))
        cy = float(np.clip(cy, 0.0, 1.0))
        ex = float(np.clip(ex, 0.0, 1.0))
        ey = float(np.clip(ey, 0.0, 1.0))

        xc_phys = cx * field.xreal + field.xoff
        yc_phys = cy * field.yreal + field.yoff
        xe_phys = ex * field.xreal + field.xoff
        ye_phys = ey * field.yreal + field.yoff

        xs = (np.arange(xres) + 0.5) * field.dx + field.xoff
        ys = (np.arange(yres) + 0.5) * field.dy + field.yoff
        gx, gy = np.meshgrid(xs, ys)

        r = np.hypot(gx - xc_phys, gy - yc_phys).ravel()
        values = field.data.ravel()

        r_max = float(np.hypot(xe_phys - xc_phys, ye_phys - yc_phys))
        if r_max <= 0.0:
            r_max = max(field.dx, field.dy)

        bin_edges = np.linspace(0.0, r_max, n_bins + 1)
        mask = r <= r_max
        idx = np.clip(
            np.floor(n_bins * r[mask] / r_max).astype(np.intp), 0, n_bins - 1
        )

        sums = np.zeros(n_bins)
        counts = np.zeros(n_bins, dtype=np.intp)
        np.add.at(sums, idx, values[mask])
        np.add.at(counts, idx, 1)

        with np.errstate(invalid="ignore"):
            profile = np.where(counts > 0, sums / counts, np.nan)

        centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

        emit_overlay({
            "kind": "radial_profile",
            "section_title": "Radial Profile",
            "image": encode_preview(render_datafield_preview(field, field.colormap)),
            "cx": cx,
            "cy": cy,
            "ex": ex,
            "ey": ey,
        })

        return (LineData(
            data=profile,
            x_axis=centers,
            x_unit=field.si_unit_xy,
            y_unit=field.si_unit_z,
        ),)
