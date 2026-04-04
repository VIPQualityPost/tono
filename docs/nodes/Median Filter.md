# Median Filter

Apply a median filter to a DATA_FIELD. Equivalent to gwy_data_field_filter_median.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered | DATA_FIELD | Median-filtered field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| size | INT | 3 | Kernel size (side length) in pixels; odd values only (1-21) |

## Notes

- The median filter is applied with a square kernel; non-square (e.g. rectangular) kernels are not supported.
- Large kernel sizes are significantly slower than the Gaussian filter for the same smoothing extent.
