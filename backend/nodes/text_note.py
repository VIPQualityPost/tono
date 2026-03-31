from __future__ import annotations

from backend.node_registry import register_node


@register_node(display_name="Text Note")
class TextNote:
    """A floating text card for annotating workflows. Supports Markdown."""

    CATEGORY = "Canvas"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "default": "# Guide\n\nDouble-click to edit this note.\n\n- Step 1\n- Step 2",
                    "multiline": True,
                }),
                "color": (["default", "blue", "green", "yellow", "red", "purple"], {
                    "default": "default",
                }),
            },
        }

    OUTPUTS = ()
    FUNCTION = "noop"

    def noop(self, text: str, color: str = "default") -> tuple:
        return ()
