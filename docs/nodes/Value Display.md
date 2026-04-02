# Value Display

Display a FLOAT value, or a selected numeric row from a measurement table, and pass the value through unchanged.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| value | FLOAT or RECORD_TABLE | No | Numeric value or measurement table to display; overrides the text input when connected |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| value | FLOAT | The numeric value (from socket or parsed from text) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| number_input | STRING (text input) | "0" | Manual numeric entry, e.g. "1.5 nm"; hidden when value socket is connected |
| measurement | STRING (dropdown) | "" | Row selector when a RECORD_TABLE is connected; visible only for RECORD_TABLE inputs |

## Notes

- When a RECORD_TABLE is connected, only rows with numeric values can be selected; non-numeric rows are not accessible.
- Manual text entry supports optional SI unit suffix (e.g. "1.5 nm") for display only; the output FLOAT is always the raw numeric value.
