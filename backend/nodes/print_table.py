from __future__ import annotations
from backend.node_registry import register_node
from backend.execution_context import emit_table


@register_node(display_name="Print Table")
class PrintTable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "table": ("RECORD_TABLE", {
                    "accepted_types": ["DATA_TABLE"],
                }),
            }
        }

    OUTPUTS = ()
    FUNCTION = "print_table"

    OUTPUT_NODE = True
    DESCRIPTION = "Show a measurement or record table."

    KEYWORDS = ("display", "show", "report", "view")

    def print_table(self, table: list) -> tuple:
        emit_table(table)
        return ()
