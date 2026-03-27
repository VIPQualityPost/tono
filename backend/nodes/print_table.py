from __future__ import annotations
from backend.node_registry import register_node
from backend.execution_context import emit_table


@register_node(display_name="Print Table")
class PrintTable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "table": ("ANY_TABLE",),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "print_table"

    OUTPUT_NODE = True
    DESCRIPTION = "Send a measurement or record table to the browser as a WebSocket message for display."

    _broadcast_table_fn = None
    _current_node_id: str = ""

    def print_table(self, table: list) -> tuple:
        emit_table(table)
        return ()
