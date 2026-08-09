# Correlation Averaging

Average repeats of a periodic structure to remove noise, as in Gwyddion's Correlation Averaging module (modules/process/averaging.c). The rectangle (x, y, width, height, in the field's physical units) selects one representative repeat used as the template. The field is normalised-cross-correlated with the template, local maxima above 75% of the peak are located, the template-sized patches at those positions are averaged with the correlation score as weight and copied back into the result, replacing the originals.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field containing the periodic structure |
| x | FLOAT | Yes | Left edge of the template rectangle in physical units (m) |
| y | FLOAT | Yes | Top edge of the template rectangle in physical units (m) |
| width | FLOAT | Yes | Template width in physical units (m) |
| height | FLOAT | Yes | Template height in physical units (m) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| averaged | DATA_FIELD | Field with each detected repeat replaced by the averaged template patch |
| alignment | RECORD_TABLE | Per-detected-repeat X/Y offset from the template centre (px) and correlation score |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| x | FLOAT | 0.0 | Left edge of one representative repeat, in physical units |
| y | FLOAT | 0.0 | Top edge of one representative repeat, in physical units |
| width | FLOAT | 1e-7 | Template width (one repeat period), in physical units |
| height | FLOAT | 1e-7 | Template height (one repeat period), in physical units |

## Notes

- The template rectangle is converted to pixels with Gwyddion's `rtoi()`/`rtoj()` mapping (truncation toward zero, offsets ignored): `x_px = x · xres / xreal`.
- The normalised correlation score repeats Gwyddion's `GWY_CORRELATION_NORMAL`: each pixel holds the mean of `(d - davg)·(k - kavg)` over the kernel window, divided by the product of the local RMS and the kernel RMS; positions where the kernel does not fit are set to -1.
- The score is smoothed with a Gaussian of 2 px FWHM (sigma = 2/(2·sqrt(2·ln 2))), exactly as in averaging.c, before local-maximum detection.
- Patches whose top-left corner would place them out of the field are skipped (a defensive deviation: Gwyddion would read out of bounds there).
- The alignment table reports offsets in pixels; multiply by the pixel size for physical offsets.
