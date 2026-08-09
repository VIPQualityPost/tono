# Invert Value

Invert a DATA_FIELD along the z, x, or y axis.

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

- z mode reflects every value about the data mean (`data = 2*mean - data`). This preserves the mean — when the mean is zero it reduces to plain negation.
- x mode reverses each row in place.
- y mode swaps rows top/bottom.
- Interactive invert dialogs let flips be combined; this node offers the three single-axis modes. Physical metadata (xreal, yreal, xoff, yoff, units) is preserved.
