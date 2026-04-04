"""Presentation operations -- manage presentation overlays on data fields."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Presentation Ops")
class PresentationOps:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "operation": (["logscale", "extract_presentation", "attach", "blend"],),
                "blend_factor": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "show_when_widget_value": {"operation": ["blend"]},
                }),
            },
            "optional": {
                "overlay": ("DATA_FIELD", {
                    "show_when_widget_value": {"operation": ["attach", "blend"]},
                }),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Manage presentation overlays on data fields. "
        "logscale applies logarithmic scaling for visualising data with large dynamic range. "
        "extract_presentation normalises the field to [0, 1]. "
        "attach replaces the field data with an overlay (resampled if needed). "
        "blend linearly mixes the field and overlay by a configurable factor. "
    )

    KEYWORDS = ("logscale", "normalize", "blend", "attach", "overlay")

    def process(self, field: DataField, operation: str, blend_factor: float,
                overlay: DataField | None = None) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        if operation == "logscale":
            data_pos = data - data.min() + 1e-30
            result = np.log10(data_pos)

        elif operation == "extract_presentation":
            dmin, dmax = data.min(), data.max()
            if dmax > dmin:
                result = (data - dmin) / (dmax - dmin)
            else:
                result = np.zeros_like(data)

        elif operation == "attach":
            if overlay is None:
                raise ValueError("'attach' operation requires an overlay field.")
            overlay_data = np.asarray(overlay.data, dtype=np.float64)
            result = self._match_shape(overlay_data, data.shape)

        elif operation == "blend":
            if overlay is None:
                raise ValueError("'blend' operation requires an overlay field.")
            overlay_data = np.asarray(overlay.data, dtype=np.float64)
            overlay_matched = self._match_shape(overlay_data, data.shape)
            result = (1.0 - blend_factor) * data + blend_factor * overlay_matched

        else:
            raise ValueError(f"Unknown operation: {operation!r}")

        return (field.replace(data=result),)

    @staticmethod
    def _match_shape(source: np.ndarray, target_shape: tuple[int, ...]) -> np.ndarray:
        """Resample *source* to *target_shape* using scipy zoom if shapes differ."""
        if source.shape == target_shape:
            return source
        from scipy.ndimage import zoom
        factors = tuple(t / s for t, s in zip(target_shape, source.shape))
        return zoom(source, factors, order=3)
