# Level Grains

Shift individual grain regions so they all share a common baseline. Uses the selected reference statistic (mean, median, or minimum) per grain to compute the offset. Useful for consistent grain height comparisons. Equivalent to Gwyddion's level_grains.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface data |
| mask | IMAGE | Yes | Binary mask defining grain regions |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with grains shifted to a common baseline |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| reference | dropdown | mean | Per-grain reference: mean, median, or minimum height |

## Notes

- Each connected region in the mask is treated as a separate grain.
- The target baseline is the average of all per-grain reference values.
- Use "minimum" reference when grains sit on different substrate heights and you want to align their bases.
- Combine with Grain Analysis to verify height distributions after leveling.
