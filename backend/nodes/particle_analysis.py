from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.nodes.helpers import _square_unit


@register_node(display_name="Particle Analysis")
class ParticleAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
            }
        }

    RETURN_TYPES = ("RECORD_TABLE",)
    RETURN_NAMES = ("particle_stats",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Label connected particle regions in a binary mask and compute per-particle "
        "statistics: area, equivalent diameter, mean/max height, bounding box. "
        "Equivalent to gwy_data_field_particles_get_values."
    )

    def process(self, field: DataField, mask: np.ndarray, min_size: int) -> tuple:
        from scipy.ndimage import label

        binary = (mask > 127).astype(np.int32)
        labeled, n_particles = label(binary)

        pixel_area = field.dx * field.dy
        xy_unit = str(field.si_unit_xy or "").strip()
        z_unit = str(field.si_unit_z or "").strip()

        rows = RecordTable()
        for pid in range(1, n_particles + 1):
            particle_pixels = labeled == pid
            area_px = int(particle_pixels.sum())
            if area_px < min_size:
                continue

            area_m2 = area_px * pixel_area
            equiv_diam = float(2.0 * np.sqrt(area_m2 / np.pi))

            heights = field.data[particle_pixels]
            mean_h = float(heights.mean())
            max_h = float(heights.max())

            ys, xs = np.where(particle_pixels)
            bbox = f"({int(xs.min())},{int(ys.min())})-({int(xs.max())},{int(ys.max())})"

            rows.append({
                "particle_id":  pid,
                "area_px":      area_px,
                "area_px_unit": _square_unit("px"),
                "area_m2":      area_m2,
                "area_m2_unit": _square_unit(xy_unit),
                "equiv_diam_m": equiv_diam,
                "equiv_diam_m_unit": xy_unit,
                "mean_height":  mean_h,
                "mean_height_unit": z_unit,
                "max_height":   max_h,
                "max_height_unit": z_unit,
                "bbox":         bbox,
            })

        return (rows,)
