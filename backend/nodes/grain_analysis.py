from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, DataTable
from backend.nodes.helpers import _square_unit, mask_to_bool


@register_node(display_name="Grain Analysis")
class GrainAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_TABLE', 'grain_stats'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Label connected grain regions in a binary mask and compute per-grain "
        "statistics: area, equivalent diameter, mean/max height, bounding box. "
    )

    KEYWORDS = ("particle", "blob", "label", "connected components", "area")

    def process(self, field: DataField, mask: np.ndarray, min_size: int) -> tuple:
        from scipy.ndimage import label

        binary = mask_to_bool(mask).astype(np.int32)
        labeled, n_grains = label(binary)

        pixel_area = field.dx * field.dy
        xy_unit = str(field.si_unit_xy or "").strip()
        z_unit = str(field.si_unit_z or "").strip()

        rows = DataTable()
        for gid in range(1, n_grains + 1):
            grain_pixels = labeled == gid
            area_px = int(grain_pixels.sum())
            if area_px < min_size:
                continue

            area_m2 = area_px * pixel_area
            equiv_diam = float(2.0 * np.sqrt(area_m2 / np.pi))

            heights = field.data[grain_pixels]
            mean_h = float(heights.mean())
            max_h = float(heights.max())

            ys, xs = np.where(grain_pixels)
            bbox = f"({int(xs.min())},{int(ys.min())})-({int(xs.max())},{int(ys.max())})"

            rows.append({
                "grain_id":     gid,
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
