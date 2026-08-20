# Flatten

Fit and subtract a least-squares plane, then re-offset every row so its usable (unmasked) pixels share one level. The row alignment removes per-row scan DC offsets that no single plane can represent, which recovers a flat grating from raw unleveled rows.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to flatten |
| mask | IMAGE | No | Binary mask for selecting which pixels define the background |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| flattened | DATA_FIELD | Plane removed and rows aligned to the unmasked level |
| plane | RECORD_TABLE | Fitted plane offset (in the field's z unit) and tilt angles X/Y in degrees |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| masking | dropdown | exclude | How to use the mask: ignore (use all pixels), include (fit background to masked pixels only), or exclude (exclude masked pixels from the background) |

## Notes

- Mask the pits (exclude is the default) so they do not bias the background fit; everything unmasked is treated as background.
- Rows are always re-offset after the plane subtraction: each row's usable pixels are brought to the landing level (rows without masked pixels, or the global usable level when no mask is used). Flat rows and the areas between pits end up on one level, reconstructing a flat grating from uncorrected rows.
- When masking is include or exclude, the background region must contain at least three non-collinear pixels to fit a plane.
