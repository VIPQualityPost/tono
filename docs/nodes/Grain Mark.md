# Grain Mark

Mark grains by thresholding height, slope magnitude, or curvature. Thresholds are relative (0–1) to the data range. Small regions below min_size pixels are removed. Equivalent to Gwyddion's grain_mark.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask of marked grains |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| criterion | dropdown | height | What to threshold: height, slope, or curvature |
| threshold_low | FLOAT | 0.3 | Lower bound of the normalized threshold range (0–1) |
| threshold_high | FLOAT | 1.0 | Upper bound of the normalized threshold range (0–1) |
| min_size | INT | 10 | Minimum grain size in pixels; smaller regions are removed (1–100000) |
| inverted | BOOLEAN | False | Invert the mask to mark valleys instead of peaks |

## Notes

- Thresholds are relative to the data range: 0.0 = minimum value, 1.0 = maximum value.
- "slope" uses Sobel gradient magnitude — useful for marking edges and steep features.
- "curvature" uses the Laplacian — useful for marking bumps or pits regardless of absolute height.
- Use inverted=True to mark valleys, pores, or depressions instead of raised features.
- For Otsu-based automatic thresholding, use the Threshold Mask node instead.
