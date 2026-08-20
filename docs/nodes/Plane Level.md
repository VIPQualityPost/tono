# Plane Level

Fit and subtract a least-squares plane from the data. Supports include/exclude mask fitting for flattening around features, similar to masked plane fitting workflows.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to level |
| mask | IMAGE | No | Binary mask for selecting which pixels to include in the plane fit |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with the fitted plane subtracted |
| plane | RECORD_TABLE | Fitted plane offset (in the field's z unit) and tilt angles X/Y in degrees |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| masking | dropdown | exclude | How to use the mask: ignore (use all pixels), include (fit plane to masked pixels only), or exclude (exclude masked pixels from fit) |

## Notes

- When masking is include or exclude, the unmasked/masked region must contain at least three non-collinear pixels to fit a plane.
