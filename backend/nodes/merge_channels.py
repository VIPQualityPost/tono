from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


def _channel_to_uint8(data: np.ndarray, scaling: str, offset: float, scale: float) -> np.ndarray:
    """Map a channel's values into 0..255 following the colormap scaling mode.

    Auto mode stretches each channel's full data range to 0..255; manual mode
    maps ``(value - offset) / scale`` to 0..255, clipping outside [0, 1].
    """
    values = np.asarray(data, dtype=np.float64)
    if scaling == "auto":
        vmin, vmax = float(values.min()), float(values.max())
        if vmax > vmin:
            normalized = (values - vmin) / (vmax - vmin)
        else:
            normalized = np.zeros_like(values)
    elif scaling == "manual":
        if not np.isfinite(scale) or scale <= 0.0:
            raise ValueError(f"Manual scale must be a positive number, got {scale!r}")
        normalized = np.clip((values - float(offset)) / float(scale), 0.0, 1.0)
    else:
        raise ValueError(f"Unknown scaling mode: {scaling!r}")
    return np.round(normalized * 255.0).astype(np.uint8)


@register_node(display_name="Merge")
class MergeChannels:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "red": ("DATA_FIELD",),
                "green": ("DATA_FIELD",),
                "blue": ("DATA_FIELD",),
                "scaling": (["auto", "manual"], {"default": "auto"}),
                "offset": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e18,
                    "max": 1e18,
                    "step": 0.001,
                    "show_when_widget_value": {"scaling": ["manual"]},
                }),
                "scale": ("FLOAT", {
                    "default": 1.0,
                    "min": 1e-18,
                    "max": 1e18,
                    "step": 0.001,
                    "show_when_widget_value": {"scaling": ["manual"]},
                }),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'image'),
    )
    FUNCTION = "process"

    CATEGORY = "Geometry"

    DESCRIPTION = (
        "Merge three data fields into a single RGB image. Each channel is scaled "
        "to 0..255 either automatically (full range of the channel) or with a "
        "user-provided offset and scale, then combined as red, green and blue."
    )

    KEYWORDS = ("rgb", "compose", "channel", "color", "color", "combine")

    def process(
        self,
        red: DataField,
        green: DataField,
        blue: DataField,
        scaling: str,
        offset: float,
        scale: float,
    ) -> tuple:
        shape = red.data.shape
        for name, channel in (("green", green), ("blue", blue)):
            if channel.data.shape != shape:
                raise ValueError(
                    f"All channels must have the same resolution: "
                    f"red {shape} vs {name} {channel.data.shape}"
                )

        r = _channel_to_uint8(red.data, scaling, offset, scale)
        g = _channel_to_uint8(green.data, scaling, offset, scale)
        b = _channel_to_uint8(blue.data, scaling, offset, scale)

        image = np.stack([r, g, b], axis=-1)

        return (image,)
