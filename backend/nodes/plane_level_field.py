from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


def _normalize_mask(mask: np.ndarray | None, shape: tuple[int, int]) -> np.ndarray | None:
    if mask is None:
        return None

    mask_array = np.asarray(mask)
    if mask_array.shape[:2] != shape:
        raise ValueError(f"Mask shape {mask_array.shape} does not match field shape {shape}.")
    return mask_array > 127


def _fit_plane(
    data: np.ndarray,
    mask: np.ndarray | None,
    masking: str,
) -> tuple[float, float, float, np.ndarray, np.ndarray]:
    yres, xres = data.shape
    x = np.linspace(0.0, 1.0, xres)
    y = np.linspace(0.0, 1.0, yres)
    xx, yy = np.meshgrid(x, y)

    if mask is None or masking == "ignore":
        valid = np.ones(data.shape, dtype=bool)
    elif masking == "include":
        valid = mask
    elif masking == "exclude":
        valid = ~mask
    else:
        raise ValueError(f"Unknown masking mode: {masking}")

    if np.count_nonzero(valid) < 3:
        raise ValueError("Plane Level requires at least three usable pixels for fitting.")

    A = np.column_stack([
        np.ones(int(np.count_nonzero(valid)), dtype=np.float64),
        xx[valid].ravel(),
        yy[valid].ravel(),
    ])
    z = data[valid].ravel()
    coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
    pa, pbx, pby = coeffs
    return float(pa), float(pbx), float(pby), xx, yy


@register_node(display_name="Plane Level")
class PlaneLevelField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "masking": (["ignore", "include", "exclude"], {"default": "ignore"}),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("leveled",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit and subtract a least-squares plane from the data. Supports include/exclude mask fitting "
        "for flattening around features, similar to masked plane fitting workflows in Gwyddion."
    )

    def process(
        self,
        field: DataField,
        masking: str = "ignore",
        mask: np.ndarray | None = None,
    ) -> tuple:
        data = field.data.copy()
        mask_array = _normalize_mask(mask, data.shape)
        pa, pbx, pby, xx, yy = _fit_plane(data, mask_array, masking)

        plane = (pa + pbx * xx + pby * yy)
        return (field.replace(data=data - plane),)
