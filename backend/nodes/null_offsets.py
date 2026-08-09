from __future__ import annotations

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Null Offsets")
class NullOffsets:
    """Set a DATA_FIELD's x/y offsets to zero (Gwyddion `null_offsets`)."""

    CATEGORY = "Level & Correct"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Set the physical offset (xoff, yoff) of a DATA_FIELD to zero. The data "
        "values themselves are unchanged — only the position of the upper-left "
        "corner in physical coordinates is reset, so the physical origin moves to "
        "the upper-left corner of the field."
    )

    KEYWORDS = ("offset", "origin", "position", "xoff", "yoff", "null")

    def process(self, field: DataField) -> tuple:
        # gwy_data_field_set_xoffset/set_yoffset(0.0)
        return (field.replace(data=field.data.copy(), xoff=0.0, yoff=0.0),)
