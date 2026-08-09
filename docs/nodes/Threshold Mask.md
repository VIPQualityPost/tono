# Threshold Mask

Create a binary mask by thresholding data. Otsu automatically finds the optimal threshold. Equivalent to Gwyddion's threshold and otsu_threshold modules.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to threshold |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask (white = selected pixels) |
| threshold | FLOAT | Effective threshold value applied (Otsu result for the otsu method), in the field's z unit |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | absolute | Thresholding method: absolute (raw data value), relative (fraction of min-max range), or otsu (automatic Otsu threshold) |
| threshold | FLOAT | 0.0 | Threshold value; for absolute: raw z value; for relative: fraction 0-1; ignored for otsu (socket-only input) |
| direction | dropdown | above | Which pixels to select: above or below the threshold |

## Notes

- For the relative method, the threshold fraction is applied to the full data range [min, max].
- Otsu thresholding may not give meaningful results on non-bimodal height distributions.
