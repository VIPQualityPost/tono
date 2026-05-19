# Zero Maximum

Shift all values so the maximum is exactly zero. All resulting values will be zero or negative.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to level |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with maximum subtracted |

## Notes

- Equivalent to subtracting the global maximum from every pixel.
- Useful when the highest point should represent the zero reference.
