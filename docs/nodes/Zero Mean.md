# Zero Mean

Shift all values so the mean is exactly zero. A pure offset subtraction — no plane fit or polynomial involved.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to level |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with mean subtracted |

## Notes

- Equivalent to subtracting a constant (the mean) from every pixel.
- Does not change relative height differences — only shifts the overall offset.
