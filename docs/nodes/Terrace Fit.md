# Terrace Fit

Segment a surface into flat terraces separated by atomic steps, fit a polynomial to each terrace, and extract step heights. Set n_terraces=0 for automatic detection via histogram clustering. Equivalent to Gwyddion's terracefit.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface with step/terrace features |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Residual, fitted surface, or label map |
| step_heights | RECORD_TABLE | Per-terrace heights and step height differences |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_terraces | INT | 0 | Number of terraces to fit; 0 = auto-detect from histogram peaks (0–50) |
| broadening | FLOAT | 1.0 | Smoothing factor for terrace detection; larger values merge noisy pixels (0.1–20.0) |
| poly_degree | INT | 0 | Polynomial degree per terrace: 0 = constant (flat), 1 = linear, 2 = quadratic, 3 = cubic (0–3) |
| output | dropdown | residual | Output mode: residual (original minus fit), fitted (fit surface), or labels (terrace assignment map) |

## Notes

- Use poly_degree=0 for ideal crystalline surfaces with perfectly flat terraces. Higher degrees compensate for sample curvature within each terrace.
- Auto-detection works best when terraces are well-separated in height. For noisy surfaces, increase broadening to improve terrace segmentation.
- The labels output assigns integer IDs (0, 1, 2, ...) to each terrace, ordered by height.
