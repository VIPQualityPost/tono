# Grain Cross

Correlate grain properties between two fields using a shared grain mask. Reports per-grain property pairs and the Pearson correlation coefficient. Equivalent to Gwyddion's grain_cross.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First height field |
| field_b | DATA_FIELD | Yes | Second height field |
| mask | IMAGE | Yes | Binary grain mask (white = grain) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| correlation | RECORD_TABLE | Per-grain property pairs and Pearson correlation coefficient |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| property_a | dropdown | mean_height | Property to compute from field_a: area, mean_height, max_height, or volume |
| property_b | dropdown | max_height | Property to compute from field_b: area, mean_height, max_height, or volume |
| min_size | INT | 10 | Minimum grain area in pixels; smaller grains are excluded (1–100000) |

## Notes

- Grains are identified by connected-component labelling (`scipy.ndimage.label`) on the binary mask.
- The **area** property uses physical pixel area (dx * dy). **Volume** integrates height above the mean of non-grain pixels.
- Each table row contains one grain's property pair formatted as "value_a / value_b".
- The final row reports the Pearson correlation coefficient r between the two property vectors (requires at least 2 grains).
- Both fields must have the same pixel dimensions as the mask.
