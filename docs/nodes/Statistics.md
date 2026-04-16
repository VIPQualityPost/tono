# Statistics

Compute basic surface statistics: min, max, mean, RMS roughness, median, and skewness. Equivalent to gwy_data_field_get_min/max/avg/rms.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to analyze |
| mask | IMAGE | No | Optional binary mask — only pixels inside the mask contribute to the statistics |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| stats | RECORD_TABLE | Table of statistical quantities with values and units |

## Controls

None.

## Notes

- When a mask is provided, it must match the field's pixel resolution. Only pixels where the mask is non-zero are included in the statistics.
