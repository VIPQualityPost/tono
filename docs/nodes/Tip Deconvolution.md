# Tip Deconvolution

Reconstruct the true surface from a tip-broadened measured AFM image. Uses morphological grey erosion (Villarrubia algorithm). Equivalent to gwy_tip_erosion (tip.c).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Measured AFM image |
| tip | DATA_FIELD | Yes | Tip shape field, e.g. from Tip Model or Blind Tip Estimate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| surface | DATA_FIELD | Reconstructed true surface |

## Controls

None.

## Notes

- The tip pixel size must match the image pixel size exactly; mismatched calibrations will produce incorrect results.
- Deconvolution can only reduce tip broadening; it cannot recover information lost below the noise floor.
- Very large tip sizes are slow due to the nested loop over all tip pixels.
