"""Outlier masking — mark statistical outlier pixels."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import bool_to_mask, emit_mask_preview


@register_node(display_name="Outlier Mask")
class OutlierMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "sigma_threshold": ("FLOAT", {"default": 3.0, "min": 1.0, "max": 10.0, "step": 0.1}),
                "mode": (["both", "high", "low"], {"default": "both"}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Create a mask marking pixels that deviate more than N standard "
        "deviations from the mean. Mode selects whether to flag high outliers, "
        "low outliers, or both. Quick way to identify noise spikes and defects. "
    )

    KEYWORDS = ("sigma", "zscore", "spikes", "defect", "anomaly", "despeckle")

    def process(self, field: DataField, sigma_threshold: float, mode: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        mean = data.mean()
        std = data.std()

        if std < 1e-30:
            mask = bool_to_mask(np.zeros(data.shape, dtype=bool))
            emit_mask_preview(field, mask)
            return (mask,)

        z = (data - mean) / std

        if mode == "both":
            outliers = np.abs(z) > sigma_threshold
        elif mode == "high":
            outliers = z > sigma_threshold
        elif mode == "low":
            outliers = z < -sigma_threshold
        else:
            raise ValueError(f"Unknown mode: {mode!r}")

        mask = bool_to_mask(outliers)
        emit_mask_preview(field, mask)

        return (mask,)
