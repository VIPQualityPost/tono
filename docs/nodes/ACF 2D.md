# ACF 2D

Compute the two-dimensional autocorrelation function with Gwyddion-style mean or plane levelling before correlation. The output is centered on zero shift and uses default half-range extents.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| acf | DATA_FIELD | 2D autocorrelation field centered on zero shift |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| level | dropdown | mean | Pre-processing applied before correlation: mean subtraction, plane subtraction, or none |

## Notes

- Output is not normalized to [−1, 1]; peak value equals the field variance.
- Plane levelling assumes a linear trend; strongly curved surfaces may not detrend correctly.
