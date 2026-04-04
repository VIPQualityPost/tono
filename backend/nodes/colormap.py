from __future__ import annotations
import json
from backend.node_registry import register_node
from backend.data_types import COLORMAPS, DEFAULT_CUSTOM_COLORMAP_STOPS, normalize_colormap_spec


@register_node(display_name="Color Map")
class ColorMap:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["preset", "custom"], {"default": "preset"}),
                "preset": (list(COLORMAPS), {
                    "default": "viridis",
                    "show_when_widget_value": {"mode": ["preset"]},
                }),
                "stops": ("STRING", {
                    "default": json.dumps(list(DEFAULT_CUSTOM_COLORMAP_STOPS)),
                    "colormap_stops": True,
                    "show_when_widget_value": {"mode": ["custom"]},
                }),
            }
        }

    OUTPUTS = (
        ('COLORMAP', 'colormap'),
    )
    FUNCTION = "build"

    DESCRIPTION = (
        "Build a reusable colormap. Choose a preset, or create a custom gradient with min/max colours "
        "and any number of intermediate stops."
    )

    KEYWORDS = ("colour", "palette", "lut", "gradient")

    def build(self, mode: str, preset: str, stops: str | None = None, stops_json: str | None = None) -> tuple:
        if mode == "preset":
            return ({"mode": "preset", "preset": normalize_colormap_spec(preset)},)

        try:
            raw_stops = stops if stops is not None else stops_json
            stops_data = json.loads(raw_stops or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("Custom colormap stops must be valid JSON.") from exc

        spec = normalize_colormap_spec({"mode": "custom", "stops": stops_data}, fallback=None)
        if not (isinstance(spec, dict) and spec.get("mode") == "custom"):
            raise ValueError("Custom colormap must include at least min and max colours.")
        return (spec,)
