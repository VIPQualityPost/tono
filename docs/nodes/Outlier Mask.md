# Outlier Mask

Create a mask marking pixels that deviate more than N standard deviations from the mean. Quick way to identify noise spikes and defects. Equivalent to Gwyddion's outliers.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask of outlier pixels |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| sigma_threshold | FLOAT | 3.0 | Number of standard deviations beyond which a pixel is an outlier (1.0–10.0) |
| mode | dropdown | both | Which outliers to flag: both (high and low), high only, or low only |

## Notes

- A pixel is flagged if its z-score (data - mean) / std exceeds the threshold.
- 3σ catches ~0.3% of pixels in a Gaussian distribution. Use 2σ for aggressive filtering or 5σ for conservative.
- The resulting mask can be fed to Laplace Interpolation or Fractal Interpolation to fill the defects.
- For a uniform (constant) field, no pixels are flagged regardless of threshold.
