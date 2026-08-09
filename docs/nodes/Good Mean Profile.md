# Good Mean Profile

Calculate a good average row profile from one image or from two images of repeated scanning of the same feature. In single mode each column is averaged over all scan rows with a trimmed mean; in multiple mode outliers between the two images are rejected before averaging. The corrected field replaces pixels outside the good-value band with the profile value.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field (or first scan of the feature) |
| second_field | DATA_FIELD | No | Second scan of the same feature, required in multiple mode |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Field with out-of-band pixels replaced by the good mean profile value |
| profile | LINE | Mean row profile in physical units (x: lateral position, y: value units) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | single | single: one image, trimmed mean over rows per column; multiple: two images with percentile-based outlier rejection |
| trim_fraction | FLOAT | 0.05 | Fraction of extremes to discard in single mode (trimmed per column) and of the difference distribution treated as outliers in multiple mode (0-0.9999) |

## Notes

- Single mode mirrors `good_profile_do_single()`: `ntrim = round(0.5*trim_fraction*yres)` samples are discarded from each end of every column, and the band low/high values are the rank-`ntrim` and rank-`yres-1-ntrim` column values; pixels outside the band are replaced.
- Multiple mode mirrors `good_profile_do_multiple()`: pixels whose absolute difference exceeds the `100*(1-trim_fraction)`-th percentile (midpoint interpolation) of all differences are rejected, and the profile is the column mean of the mean image over the remaining pixels.
- Unlike the reference implementation (which only outputs a mask), this node also emits a corrected field with out-of-band pixels substituted by the profile value.
