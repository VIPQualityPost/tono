"""Mask shift — translate mask by pixel offset."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool, bool_to_mask, emit_mask_preview


@register_node(display_name="Mask Shift")
class MaskShift:
    """Translate a binary mask by an integer pixel offset."""

    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
                "shift_x": ("INT", {"default": 0, "min": -1000, "max": 1000, "step": 1}),
                "shift_y": ("INT", {"default": 0, "min": -1000, "max": 1000, "step": 1}),
                "border_mode": (["zero", "wrap", "mirror"],),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Translate a binary mask by an integer pixel offset. "
        "Choose how out-of-bounds regions are filled: zero (empty), "
        "wrap (periodic roll), or mirror (reflected padding)."
    )

    def process(self, mask: np.ndarray, shift_x: int, shift_y: int,
                border_mode: str, field: DataField | None = None) -> tuple:
        binary = mask_to_bool(mask)

        if border_mode == "wrap":
            result = self._shift_wrap(binary, shift_x, shift_y)
        elif border_mode == "zero":
            result = self._shift_zero(binary, shift_x, shift_y)
        elif border_mode == "mirror":
            result = self._shift_mirror(binary, shift_x, shift_y)
        else:
            raise ValueError(f"Unknown border mode: {border_mode}")

        out = bool_to_mask(result)
        emit_mask_preview(field, out)
        return (out,)

    @staticmethod
    def _shift_wrap(binary: np.ndarray, sx: int, sy: int) -> np.ndarray:
        """Shift with periodic wrapping (np.roll)."""
        return np.roll(np.roll(binary, sx, axis=1), sy, axis=0)

    @staticmethod
    def _shift_zero(binary: np.ndarray, sx: int, sy: int) -> np.ndarray:
        """Shift then zero-fill the wrapped region."""
        result = np.roll(np.roll(binary, sx, axis=1), sy, axis=0)
        h, w = result.shape[:2]

        # Zero-fill columns wrapped by horizontal shift
        if sx > 0:
            result[:, :sx] = False
        elif sx < 0:
            result[:, w + sx:] = False

        # Zero-fill rows wrapped by vertical shift
        if sy > 0:
            result[:sy, :] = False
        elif sy < 0:
            result[h + sy:, :] = False

        return result

    @staticmethod
    def _shift_mirror(binary: np.ndarray, sx: int, sy: int) -> np.ndarray:
        """Shift using reflected padding then crop back to original size."""
        h, w = binary.shape[:2]
        abs_sx = abs(sx)
        abs_sy = abs(sy)

        # Pad with reflect mode
        padded = np.pad(binary, ((abs_sy, abs_sy), (abs_sx, abs_sx)), mode="reflect")

        # Crop with offset to achieve the shift
        row_start = abs_sy - sy
        col_start = abs_sx - sx
        return padded[row_start:row_start + h, col_start:col_start + w]
