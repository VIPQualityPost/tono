# Fix Zero

Shift data so that the minimum, mean, or median value becomes zero. Equivalent to fix_zero in Gwyddion's level.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| zeroed | DATA_FIELD | Field shifted so the chosen reference is at zero |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | min | Reference value to set to zero: min (lowest pixel), mean (average), or median |

## Limitations

- None.
