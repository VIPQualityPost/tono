from __future__ import annotations
from backend.node_registry import register_node
from backend.execution_context import emit_table, emit_value
from backend.data_types import RecordTable
from backend.nodes.helpers import _measurement_entry, _measurement_value, _scalar_payload, parse_number_with_unit


@register_node(display_name="Value Display")
class ValueIO:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "number_input": ("STRING", {
                    "text_input": True,
                    "default": "0",
                    "placeholder": "e.g. 1.5 nm",
                    "hide_when_input_connected": "value",
                    "hide_label": True,
                }),
                "measurement": ("STRING", {
                    "default": "",
                    "choices_from_measure_input": "value",
                    "show_when_source_type": {
                        "value": ["RECORD_TABLE"],
                    },
                }),
            },
            "optional": {
                "value": ("FLOAT", {
                    "accepted_types": ["RECORD_TABLE"],
                    "socket_only": True,
                }),
            },
        }

    OUTPUTS = (
        ('FLOAT', 'value'),
    )
    FUNCTION = "display_value"

    DESCRIPTION = "Display a FLOAT, or a selected numeric row from a measurement table, and pass the value through unchanged."

    _broadcast_value_fn = None
    _current_node_id: str = ""

    def display_value(self, number_input: str = "0", value=None, measurement: str = "") -> tuple:
        unit = ""
        if isinstance(value, RecordTable):
            emit_table(value)
            row = _measurement_entry(value, measurement)
            numeric = _measurement_value(value, measurement)
            unit = row.get("unit", "") if isinstance(row.get("unit"), str) else ""
        elif value is not None:
            numeric = float(value)
        else:
            numeric, unit = parse_number_with_unit(str(number_input))
        emit_value(_scalar_payload(numeric, unit))
        return (numeric,)
