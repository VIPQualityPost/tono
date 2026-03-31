# Kuwahara Filter

Edge-preserving smoothing using Kuwahara's minimum-variance quadrant method. Unlike Gaussian blur, sharp boundaries are preserved. Equivalent to Gwyddion's Kuwahara filter.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered | DATA_FIELD | Smoothed field with preserved edges |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| iterations | INT | 1 | Number of times the 5×5 Kuwahara pass is applied (1–20) |

## Limitations

- The kernel is fixed at 5×5 pixels; coarser smoothing requires more iterations.
- Multiple iterations increase processing time proportionally; 20 iterations on a large field may be slow.
