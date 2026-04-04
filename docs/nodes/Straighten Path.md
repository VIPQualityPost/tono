# Straighten Path

Extract a cross-section along an arbitrary curved path defined by control points. The path is interpolated between points and data is sampled along it using `scipy.ndimage.map_coordinates`. Equivalent to Gwyddion's straighten_path.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| straightened | DATA_FIELD | Straightened cross-section; width = n_samples, height = thickness |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| points_x | STRING | "0.25, 0.5, 0.75" | Comma-separated fractional x-coordinates of control points (0.0–1.0) |
| points_y | STRING | "0.5, 0.3, 0.5" | Comma-separated fractional y-coordinates of control points (0.0–1.0) |
| thickness | INT | 1 | Width of the sampled strip perpendicular to the path, in pixels (1–100) |
| n_samples | INT | 256 | Number of sample points along the path (10–2048) |

## Notes

- Control points are specified as fractions of the image dimensions (0 = left/top edge, 1 = right/bottom edge). At least 2 points are required.
- Points are connected by linear interpolation; the path is sampled at n_samples evenly spaced positions.
- When thickness > 1, samples are taken along the local normal direction at each path position, producing a 2D strip rather than a single line.
- The output xreal equals the physical path length (computed from pixel spacing), and yreal equals thickness times the pixel size.
- Bilinear interpolation (order=1) is used with nearest-edge boundary handling.
