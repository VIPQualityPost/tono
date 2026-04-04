# Slope Distribution

Compute the angular slope distribution of a DATA_FIELD surface. Equivalent to Gwyddion's slope_dist module (slope_dist.c).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| distribution | LINE | Slope distribution histogram |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| distribution | dropdown | theta | Distribution type: theta (inclination angle, probability density in 1/deg), phi (azimuthal direction, weighted by slope², 0-360°), or gradient (slope magnitude, probability density in 1/(z/xy)) |
| n_bins | INT | 90 | Number of histogram bins (10-1000) |

## Notes

- The gradient magnitude distribution requires valid physical xy and z units for correct normalization.
- phi distribution is weighted by slope squared; flat surfaces with near-zero slopes produce a noisy azimuthal distribution.
