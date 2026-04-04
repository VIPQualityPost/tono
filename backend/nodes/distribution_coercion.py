"""Distribution coercion — transform data to match a target distribution."""

from __future__ import annotations

import numpy as np
from math import ceil
from scipy.stats import norm

from backend.node_registry import register_node
from backend.data_types import DataField


def _coerce_block(data: np.ndarray, distribution: str, n_levels: int) -> np.ndarray:
    """Coerce a flat or 2-D block to the target distribution, returning same shape."""
    shape = data.shape
    flat = data.ravel().astype(np.float64)
    n_pixels = flat.size
    if n_pixels == 0:
        return data.copy()

    indices = np.argsort(flat, kind="mergesort")

    if distribution == "uniform":
        target = np.linspace(float(flat.min()), float(flat.max()), n_pixels)
    elif distribution == "gaussian":
        eps = 0.5 / n_pixels
        quantiles = np.linspace(eps, 1.0 - eps, n_pixels)
        target = norm.ppf(quantiles) * float(flat.std()) + float(flat.mean())
    elif distribution == "levels":
        n_levels = max(2, int(n_levels))
        level_values = np.linspace(float(flat.min()), float(flat.max()), n_levels)
        target = np.repeat(level_values, ceil(n_pixels / n_levels))[:n_pixels]
    else:
        raise ValueError(f"Unknown distribution: {distribution}")

    result = np.empty_like(flat)
    result[indices] = target
    return result.reshape(shape)


@register_node(display_name="Distribution Coercion")
class DistributionCoercion:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "distribution": (["uniform", "gaussian", "levels"], {"default": "uniform"}),
                "n_levels": ("INT", {
                    "default": 4,
                    "min": 2,
                    "max": 1000,
                    "show_when_widget_value": {"distribution": ["levels"]},
                }),
                "processing": (["field", "rows"], {"default": "field"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Transform pixel values so their distribution matches a target shape "
        "(uniform, Gaussian, or discrete levels) using rank-based reassignment. "
    )

    KEYWORDS = ("coerce", "histogram matching", "equalize", "uniform", "gaussian", "quantize")

    def process(self, field: DataField, distribution: str, n_levels: int,
                processing: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        if processing == "rows":
            result = np.empty_like(data)
            for i in range(data.shape[0]):
                result[i] = _coerce_block(data[i], distribution, n_levels)
        else:
            result = _coerce_block(data, distribution, n_levels)

        return (field.replace(data=result),)
