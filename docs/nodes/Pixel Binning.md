# Pixel Binning

Downsample a DATA_FIELD by grouping pixels into NxN blocks and reducing each block to a single value. Supports mean, sum, and median reduction methods.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to downsample |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| binned | DATA_FIELD | Downsampled field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| bin_size | INT | 2 | Side length of the square binning block in pixels (2-64) |
| method | dropdown | mean | Reduction method per block: mean (average), sum (total), or median (middle value) |

## Notes

- Pixels at the right and bottom edges that do not fill a complete block are trimmed and discarded.
- The output dimensions are floor(width / bin_size) x floor(height / bin_size).
- Mean binning improves signal-to-noise ratio by a factor of bin_size. Sum binning preserves total signal (useful for count data). Median binning is robust to outlier pixels within each block.
- Physical dimensions (real-space size) of the output field are updated to reflect the trimmed area.
