# Image Stitch

Combine two overlapping scans into a single image. Uses cross-correlation to align the images and blends the overlap region. Equivalent to Gwyddion's merge.c / stitch.c modules.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First (reference) field |
| field_b | DATA_FIELD | Yes | Second field to stitch onto field_a |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| stitched | DATA_FIELD | Combined field |
| alignment | RECORD_TABLE | Overlap shift of field_b relative to field_a, in pixels and physical units |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| direction | dropdown | auto | How field_b is positioned relative to field_a: right, below, or auto (determined by cross-correlation) |
| blend | dropdown | linear | Overlap blending: linear (smooth transition) or none (hard cut) |

## Notes

- Auto direction uses cross-correlation to determine whether field_b is to the right or below field_a.
- Linear blending produces a smooth transition in the overlap region, avoiding visible seams.
- Both fields should have the same pixel size (dx, dy) for correct physical dimensions in the output.
- The output field's physical dimensions are updated to reflect the combined area.
