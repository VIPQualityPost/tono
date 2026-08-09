# Immerse Detail

Overlay a high-resolution detail scan onto a lower-resolution overview image. Uses sliding-window cross-correlation (coarse + fine search) to automatically locate the detail within the overview.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| overview | DATA_FIELD | Yes | Lower-resolution overview field |
| detail | DATA_FIELD | Yes | Higher-resolution detail field to place into the overview |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| combined | DATA_FIELD | Overview field with the detail region replaced or blended in |
| placement | RECORD_TABLE | Detail placement position (pixels and physical units) and match score |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| blend | dropdown | replace | How to combine the detail with the overview: replace (overwrite) or average (mean of both) |

## Notes

- If the detail has a different pixel size than the overview, it is resampled (via `scipy.ndimage.zoom`) to match the overview pixel spacing before placement.
- Alignment uses a two-pass normalized cross-correlation: a coarse search with stride, followed by a fine pixel-by-pixel search around the best coarse position.
- If the detail is larger than the overview in either dimension, the overview is returned unchanged.
- The output retains the overview's physical dimensions and metadata.
