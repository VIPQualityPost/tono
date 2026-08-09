# Multiple Profiles

Extract and compare line profiles from two fields along a chosen row or column. Supports overlay, mean, and difference modes.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First input field |
| field_b | DATA_FIELD | Yes | Second input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| profile | LINE | Resulting line profile |
| profile_b | LINE | Field B's raw line profile (same x-axis and units as profile) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| row | INT | -1 | Row (horizontal) or column (vertical) index to extract; -1 uses the centre row/column (-1-10000) |
| direction | dropdown | horizontal | Profile direction: horizontal (extract a row) or vertical (extract a column) |
| mode | dropdown | overlay | Combination mode: overlay (field_a profile only), mean (average of both), or difference (field_a minus field_b) |
| blend | FLOAT | 0.5 | Opacity of field B in the preview (0 = only A, 1 = only B). Affects the preview image only, not the extracted profile. |

## Interactive preview

The preview shows field A blended with field B and highlights the row or column being sampled. Click or drag on the image to move the line; switch between row and column extraction with the `direction` control.

## Notes

- When the two fields have different sizes, profiles are truncated to the shorter length so they can be compared element-wise.
- The x-axis of the output profile uses physical spacing (dx for horizontal, dy for vertical) from field_a.
- The output y-unit inherits field_a's z-unit.
- Difference mode is useful for visualising drift, processing artefacts, or changes between sequential scans.
