# Colormap Adjust

Adjust how a DATA_FIELD maps into its colormap without changing the underlying data — pick the colormap ramp and shift/zoom its range. offset and scale operate in normalized display coordinates; Auto resets to the full data range.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field whose colormap mapping is adjusted |
| colormap_map | COLORMAP | No | Optional colormap built by the Color Map node; overrides the colormap dropdown |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Field with updated colormap, display_offset, and display_scale metadata |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| colormap | dropdown | auto | Colormap ramp to apply. `auto` keeps the field's current colormap; pick a preset to change it |
| offset | FLOAT | 0.0 | Shift the colormap center in normalized units (-1 to 1) |
| scale | FLOAT | 1.0 | Zoom the colormap range (0.05-4.0); values below 1 stretch contrast |
| auto | BUTTON | — | Reset offset to 0 and scale to 1 (full data range) |

## Notes

- Only the display mapping metadata is changed; raw data values are unaffected.
- `auto` inherits the field's existing colormap, so connecting a field and adjusting only offset/scale leaves its map untouched.
- Connecting a `Color Map` node to the `colormap_map` input hides the dropdown and applies its ramp (preset or custom gradient) instead.
- Scale must be positive and finite; zero or negative values raise an error.
