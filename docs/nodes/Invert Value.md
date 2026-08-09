# Invert Value

Invert a DATA_FIELD along the z, x, or y axis. Equivalent to Gwyddion's `invert_value` basic operation in combination with the libprocess `gwy_data_field_invert` function.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to invert |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Inverted field with the same physical extents and offsets |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | z | Axis to invert: z (negate heights), x (mirror left/right), or y (mirror top/bottom) |

## Notes

- z mode follows Gwyddion's `gwy_data_field_invert(zflipped=TRUE)`: every value is reflected about the data mean (`data = 2*mean - data`). This preserves the mean — when the mean is zero it reduces to plain negation.
- x mode is `gwy_data_field_invert(xflipped=TRUE)`: each row is reversed in place.
- y mode is `gwy_data_field_invert(yflipped=TRUE)`: rows are swapped top/bottom.
- Gwyddion's interactive invert dialog lets flips be combined; this node offers the three single-axis modes. Physical metadata (xreal, yreal, xoff, yoff, units) is preserved.
