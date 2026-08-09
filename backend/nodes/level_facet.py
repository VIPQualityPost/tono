from __future__ import annotations

import numpy as np

from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.node_registry import register_node
from backend.nodes.surface_common import require_compatible_xy_z_units
from backend.nodes.helpers import normalize_mask


def _facet_cell_mask(mask: np.ndarray | None, masking: str, shape: tuple[int, int]) -> np.ndarray:
    yres, xres = shape
    if yres < 2 or xres < 2:
        return np.zeros((0, 0), dtype=bool)

    if mask is None or masking == "ignore":
        return np.ones((yres - 1, xres - 1), dtype=bool)

    m00 = mask[:-1, :-1]
    m01 = mask[:-1, 1:]
    m10 = mask[1:, :-1]
    m11 = mask[1:, 1:]

    if masking == "include":
        return m00 & m01 & m10 & m11
    if masking == "exclude":
        return ~(m00 | m01 | m10 | m11)
    raise ValueError(f"Unknown masking mode: {masking}")


def _fit_facet_plane(
    data: np.ndarray,
    dx: float,
    dy: float,
    mask: np.ndarray | None,
    masking: str,
) -> tuple[bool, float, float, float]:
    yres, xres = data.shape
    if yres < 2 or xres < 2:
        return False, 0.0, 0.0, 0.0

    dx = float(dx) if float(dx) > 0.0 else 1.0
    dy = float(dy) if float(dy) > 0.0 else 1.0

    valid = _facet_cell_mask(mask, masking, data.shape)
    nvalid = int(np.count_nonzero(valid))
    if nvalid < 4:
        return False, 0.0, 0.0, 0.0

    z00 = data[:-1, :-1]
    z01 = data[:-1, 1:]
    z10 = data[1:, :-1]
    z11 = data[1:, 1:]

    vx = 0.5 * (z11 + z01 - z10 - z00) / dx
    vy = 0.5 * (z10 + z11 - z00 - z01) / dy
    mag2 = vx * vx + vy * vy

    sigma2 = float((1.0 / 20.0) * np.mean(mag2[valid]))
    if not np.isfinite(sigma2) or sigma2 <= 0.0:
        return True, 0.0, 0.0, 0.0

    weights = np.exp(-mag2[valid] / sigma2)
    sumvz = float(np.sum(weights))
    if not np.isfinite(sumvz) or sumvz <= 0.0:
        return True, 0.0, 0.0, 0.0

    pbx = float(np.sum(vx[valid] * weights) / sumvz * dx)
    pby = float(np.sum(vy[valid] * weights) / sumvz * dy)
    pa = float(-0.5 * (pbx * xres + pby * yres))
    return True, pa, pbx, pby


def _subtract_plane(data: np.ndarray, a: float, bx: float, by: float) -> np.ndarray:
    yy, xx = np.mgrid[0:data.shape[0], 0:data.shape[1]]
    return np.asarray(data, dtype=np.float64) - (float(a) + float(bx) * xx + float(by) * yy)


def _facet_level_data(
    field: DataField,
    mask: np.ndarray | None,
    masking: str,
    *,
    max_iterations: int = 100,
    eps: float = 1e-9,
) -> tuple[np.ndarray, float, float, float]:
    working = np.asarray(field.data, dtype=np.float64).copy()
    a, bx, by = 0.0, 0.0, 0.0

    for _ in range(max(1, int(max_iterations))):
        ok, a, bx, by = _fit_facet_plane(working, field.dx, field.dy, mask, masking)
        if not ok:
            return np.asarray(field.data, dtype=np.float64).copy(), a, bx, by

        working = _subtract_plane(working, a, bx, by)
        slope_x = float(bx) / (field.dx if field.dx > 0.0 else 1.0)
        slope_y = float(by) / (field.dy if field.dy > 0.0 else 1.0)
        if slope_x * slope_x + slope_y * slope_y < float(eps):
            break

    return working, a, bx, by


@register_node(display_name="Facet Level")
class FacetLevelField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "masking": (["exclude", "include", "ignore"], {"default": "exclude"}),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
        ('RECORD_TABLE', 'plane'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Level a field by iteratively finding the dominant local facet orientation and subtracting the "
        "corresponding plane in facet-level fashion. Supports mask include/exclude "
        "selection and expects topographic data with compatible XY and Z units."
    )

    KEYWORDS = ("flatten", "tilt", "plane")

    def process(
        self,
        field: DataField,
        masking: str,
        mask: np.ndarray | None = None,
    ) -> tuple:
        require_compatible_xy_z_units(field, "Facet Level")
        mask_array = normalize_mask(mask, field.data.shape)
        leveled, a, bx, by = _facet_level_data(field, mask_array, masking, max_iterations=100)

        tilt_x_deg = float(np.degrees(np.arctan(bx / field.dx))) if field.dx > 0 else float(np.degrees(np.arctan(bx)))
        tilt_y_deg = float(np.degrees(np.arctan(by / field.dy))) if field.dy > 0 else float(np.degrees(np.arctan(by)))
        plane = RecordTable([
            {"quantity": "Plane offset", "value": a, "unit": field.si_unit_z},
            {"quantity": "Tilt X", "value": tilt_x_deg, "unit": "deg"},
            {"quantity": "Tilt Y", "value": tilt_y_deg, "unit": "deg"},
        ])
        emit_table(plane)
        return (field.replace(data=leveled), plane)
