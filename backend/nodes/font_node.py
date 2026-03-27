from __future__ import annotations
from backend.node_registry import register_node
from backend.data_types import CUSTOM_FILE_FONT, SYSTEM_DEFAULT_FONT, list_overlay_font_choices, normalize_font_spec


@register_node(display_name="Font")
class Font:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "family": ([SYSTEM_DEFAULT_FONT, *list_overlay_font_choices(), CUSTOM_FILE_FONT], {
                    "default": SYSTEM_DEFAULT_FONT,
                }),
                "font_file": ("FILE_PICKER", {
                    "default": "",
                    "show_when_widget_value": {"family": [CUSTOM_FILE_FONT]},
                }),
            }
        }

    RETURN_TYPES = ("FONT",)
    RETURN_NAMES = ("font",)
    FUNCTION = "build"

    DESCRIPTION = (
        "Build a reusable font spec for annotation overlays. Choose a discovered system font, "
        "use the default fallback stack, or point to a custom font file."
    )

    def build(self, family: str, font_file: str = "") -> tuple:
        if family == SYSTEM_DEFAULT_FONT:
            return (None,)
        if family == CUSTOM_FILE_FONT:
            return (normalize_font_spec({"path": font_file}),)
        return (normalize_font_spec({"family": family}),)
