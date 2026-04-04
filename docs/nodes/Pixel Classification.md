# Pixel Classification

Classify pixels into discrete classes based on height, slope, and/or curvature using threshold or clustering methods. Equivalent to Gwyddion's classify.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| classified | DATA_FIELD | Integer class labels (0 to n_classes-1) |
| mask | IMAGE | Binary mask of the first class (class 0) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_classes | INT | 3 | Number of output classes (2–10) |
| feature | dropdown | height | Feature used for classification: height, slope, curvature, height_slope, or all |
| method | dropdown | otsu | Thresholding method: otsu, equal_range, or quantile |

## Notes

- **Feature types**: "height" uses raw data values; "slope" uses gradient magnitude (via `np.gradient`); "curvature" uses the Laplacian (sum of second derivatives). "height_slope" and "all" stack multiple features.
- **Threshold methods** (single-feature only):
  - *otsu*: Multi-Otsu thresholding that finds thresholds minimising intra-class variance.
  - *equal_range*: Divides the feature value range into equal-width intervals.
  - *quantile*: Divides by quantiles so each class contains roughly the same number of pixels.
- **Multi-feature modes** ("height_slope", "all") ignore the method setting and use k-means clustering instead. Each feature is normalised to [0, 1] before clustering.
- The mask output contains class 0 only — use the classified field for access to all class labels.
