# Trimmed Mean

Apply a local trimmed-mean filter to a DATA_FIELD. Within each circular window, the lowest and highest fraction of pixel values are excluded before computing the mean. This provides smoothing that is more robust to outliers than a plain Gaussian or mean filter.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered | DATA_FIELD | Trimmed-mean filtered field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| radius | INT | 3 | Radius of the circular filter window in pixels (1-50) |
| trim_fraction | FLOAT | 0.1 | Fraction of values to exclude from each end of the sorted window (0.0-0.49) |

## Notes

- A trim_fraction of 0.0 gives a plain local mean (no trimming). A trim_fraction approaching 0.5 converges to the local median.
- Typical values of 0.05-0.2 effectively suppress outlier spikes while preserving smooth features better than a median filter.
- The filter uses a circular (disc-shaped) kernel; the actual window diameter is 2*radius + 1 pixels.
- More computationally expensive than a Gaussian filter due to the sorting step within each window.
