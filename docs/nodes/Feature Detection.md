# Feature Detection

Detect edges or corners in a surface using Canny edge detection or Harris corner detection. Outputs a feature map and a table of detected feature locations. Equivalent to Gwyddion's edge/corner detection in filters.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Feature map (binary edges or corner response) |
| features | RECORD_TABLE | Table of detected feature statistics and locations |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | canny | Detection method: canny (edges) or harris (corners) |
| sigma | FLOAT | 1.0 | Gaussian smoothing sigma in pixels (0.1-20.0) |
| low_threshold | FLOAT | 0.1 | Canny low hysteresis threshold (0-1) |
| high_threshold | FLOAT | 0.2 | Canny high hysteresis threshold (0-1) |
| harris_k | FLOAT | 0.05 | Harris detector sensitivity parameter (0.01-0.5) |
| min_distance | INT | 5 | Minimum distance between detected corners in pixels (1-100) |

## Notes

- **Canny**: Multi-stage edge detector with non-maximum suppression and hysteresis thresholding. Output is a binary edge map. Reports edge pixel count and edge fraction.
- **Harris**: Corner detector based on the structure tensor eigenvalues. Output is the corner response map. Reports up to 20 strongest corner locations with physical coordinates.
- Increase sigma to detect larger-scale features and suppress noise.
- For basic edge detection (Sobel, Prewitt, Laplacian), use the Edge Detect node instead.
