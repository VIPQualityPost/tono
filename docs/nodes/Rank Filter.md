# Rank Filter

Apply a general rank-order (morphological) filter to a DATA_FIELD. Selects the k-th smallest value within a local window, encompassing erosion, dilation, median, and arbitrary percentile operations. Equivalent to Gwyddion's `rank-filter.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered | DATA_FIELD | Rank-filtered field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| radius | INT | 3 | Radius of the circular filter window in pixels (1–50) |
| operation | dropdown | median | Filter operation: erosion (local minimum), dilation (local maximum), median (50th percentile), or percentile (custom rank) |
| percentile | FLOAT | 50.0 | Custom percentile rank, used only when operation is percentile (0.0–100.0) |

## Notes

- Erosion (local min) shrinks bright features and expands dark ones. Dilation (local max) does the opposite.
- Median is equivalent to percentile = 50 and provides edge-preserving smoothing.
- The percentile parameter is ignored unless operation is set to percentile. A percentile of 0 is equivalent to erosion, and 100 is equivalent to dilation.
- The filter uses a circular (disc-shaped) kernel; the actual window diameter is 2*radius + 1 pixels.
- Combining erosion followed by dilation (opening) or dilation followed by erosion (closing) can be achieved by chaining two Rank Filter nodes.
