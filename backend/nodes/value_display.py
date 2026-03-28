from __future__ import annotations
from backend.node_registry import register_node
from backend.execution_context import emit_value
from backend.data_types import MeasureTable
from backend.nodes.helpers import _measurement_entry, _measurement_value, _scalar_payload


@register_node(display_name="Value Display")
class ValueDisplay:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("FLOAT", {
                    "accepted_types": ["MEASURE_TABLE"],
                }),
                "measurement": ("STRING", {
                    "default": "",
                    "choices_from_measure_input": "value",
                    "show_when_source_type": {
                        "value": ["MEASURE_TABLE"],
                    },
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "display_value"

    DESCRIPTION = "Display a FLOAT, or a selected numeric row from a measurement table, and pass the value through unchanged."

    _broadcast_value_fn = None
    _current_node_id: str = ""

    def display_value(self, value, measurement: str = "") -> tuple:
        unit = ""
        if isinstance(value, MeasureTable):
            row = _measurement_entry(value, measurement)
            numeric = _measurement_value(value, measurement)
            unit = row.get("unit", "") if isinstance(row.get("unit"), str) else ""
        else:
            numeric = float(value)
        emit_value(_scalar_payload(numeric, unit))
        return (numeric,)
