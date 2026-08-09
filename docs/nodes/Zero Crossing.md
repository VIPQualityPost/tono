# Zero Crossing

Detect edges by finding zero crossings of the Laplacian of Gaussian (LoG). Sigma controls the Gaussian smoothing scale. Threshold filters out weak edges relative to the LoG range.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| edges | DATA_FIELD | Binary edge map (1.0 at edges, 0.0 elsewhere) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| sigma | FLOAT | 2.0 | Gaussian smoothing scale for the LoG operator (0.5-20.0) |
| threshold | FLOAT | 0.0 | Minimum edge strength as a fraction of the maximum LoG contrast; filters weak edges (0.0-1.0) |

## Notes

- The algorithm computes the Laplacian of Gaussian (via `scipy.ndimage.gaussian_laplace`), then marks pixels where adjacent values change sign (horizontal and vertical neighbours).
- Larger sigma values detect coarser features and suppress noise; smaller values pick up finer detail but are noisier.
- Threshold = 0.0 keeps all zero crossings. Increasing it towards 1.0 retains only the strongest edges.
- The output z-unit is cleared (dimensionless binary mask).
