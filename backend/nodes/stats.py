from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_value
from backend.data_types import DataField, LineData, RecordTable
from backend.nodes.helpers import (
    LINE_OPS,
    TABLE_OPS,
    ARRAY_OPS,
    _scalar_payload,
    _apply_scalar_unit,
    _common_table_unit,
    extract_numeric_table_values,
    resolve_table_column_name,
)


@register_node(display_name="Stats")
class Stats:
    """Polymorphic scalar stats node for LINE, DATA_TABLE, DATA_FIELD, or IMAGE inputs."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("DATA_FIELD", {
                    "accepted_types": ["IMAGE", "LINE", "DATA_TABLE"],
                }),
                "column": ("STRING", {
                    "default": "value",
                    "choices_from_table_input": "input",
                    "show_when_source_type": {
                        "input": ["DATA_TABLE"],
                    },
                }),
                "operation": ("STRING", {
                    "default": "mean",
                    "choices_by_source_type": {
                        "LINE": list(LINE_OPS.keys()),
                        "DATA_TABLE": list(TABLE_OPS.keys()),
                        "DATA_FIELD": list(ARRAY_OPS.keys()),
                        "IMAGE": list(ARRAY_OPS.keys()),
                    },
                    "source_type_input": "input",
                }),
            }
        }

    OUTPUTS = (
        ('FLOAT', 'value'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute a contextual scalar statistic from a LINE, record table, DATA_FIELD, or IMAGE. "
        "The available operations adapt to the connected input type."
    )

    def process(self, input, operation: str, column: str = "value") -> tuple:
        source_type, values, resolved_column = self._resolve_input_values(input, column)

        if source_type == "DATA_TABLE":
            ops = TABLE_OPS
        elif source_type == "LINE":
            ops = LINE_OPS
        else:
            ops = ARRAY_OPS

        if operation not in ops:
            raise ValueError(f"Operation '{operation}' is not valid for {source_type} input.")

        op_entry = ops[operation]
        fn = op_entry[0] if isinstance(op_entry, tuple) else op_entry
        result = fn(values)
        emit_value(
            _scalar_payload(result, self._resolve_output_unit(input, source_type, resolved_column, operation)),
        )
        return (result,)

    def _resolve_output_unit(self, input_value, source_type: str, column: str | None, operation: str) -> str:
        if source_type == "DATA_FIELD" and isinstance(input_value, DataField):
            return _apply_scalar_unit(input_value.si_unit_z, operation)

        if source_type == "LINE":
            line_entry = LINE_OPS.get(operation)
            explicit_unit = line_entry[1] if isinstance(line_entry, tuple) and len(line_entry) > 1 else ""
            if explicit_unit:
                return _apply_scalar_unit(explicit_unit, operation)
            if isinstance(input_value, LineData):
                return _apply_scalar_unit(input_value.y_unit, operation)
            return ""

        if source_type == "DATA_TABLE" and isinstance(input_value, list) and column:
            return _apply_scalar_unit(_common_table_unit(input_value, column), operation)

        return ""

    def _resolve_input_values(self, input_value, column: str) -> tuple[str, np.ndarray, str | None]:
        if isinstance(input_value, DataField):
            values = np.asarray(input_value.data, dtype=np.float64)
            return ("DATA_FIELD", values.ravel(), None)

        if isinstance(input_value, RecordTable):
            raise ValueError("Stats only accepts record tables, not measurement tables.")

        if isinstance(input_value, list):
            if not input_value:
                raise ValueError("Stats requires a non-empty record table input.")
            column_name = resolve_table_column_name(input_value, column)
            values = extract_numeric_table_values(input_value, column_name)
            if not values:
                raise ValueError(f"Column '{column_name}' has no numeric values.")
            return ("DATA_TABLE", np.asarray(values, dtype=np.float64), column_name)

        if isinstance(input_value, LineData):
            values = np.asarray(input_value.data, dtype=np.float64)
            if values.size == 0:
                raise ValueError("Stats requires a non-empty input.")
            return ("LINE", values.ravel(), None)

        if isinstance(input_value, np.ndarray):
            values = np.asarray(input_value, dtype=np.float64)
            if values.size == 0:
                raise ValueError("Stats requires a non-empty input.")
            if values.ndim == 1:
                return ("LINE", values.ravel(), None)
            return ("IMAGE", values.ravel(), None)

        raise ValueError(f"Unsupported Stats input type: {type(input_value).__name__}")
