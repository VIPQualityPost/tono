# Straighten Path

Extract a cross-section along an arbitrary curved path defined by control points. The path is interpolated between points and data is sampled along it using `scipy.ndimage.map_coordinates`.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| straightened | DATA_FIELD | Straightened cross-section; width = n_samples, height = thickness |
| profile | LINE | 1-pixel-wide profile sampled along the centerline of the path |
| length | FLOAT | Physical length of the path (in the field's lateral units) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| thickness | INT | 1 | Width of the sampled strip perpendicular to the path, in pixels (1-100) |
| n_samples | INT | 256 | Number of sample points along the path (10-2048) |

## Interactive preview

The node renders the input field with the control points and a smooth curve through them. Drag any point to reshape the path. Double-click anywhere on the image to add a new point at that location. Shift-click a point to delete it (a minimum of two points is kept). The shaded band along the curve previews the sampling thickness.

The straightened result is shown in the regular preview section below.

## Notes

- Control points are specified as fractions of the image dimensions (0 = left/top edge, 1 = right/bottom edge). At least 2 points are required.
- With 3 or more points, the path is a natural cubic spline (C² continuous) passing through each control point, matching the smooth curve drawn on the preview. With exactly 2 points the path is a straight line.
- When thickness > 1, samples are taken along the local normal direction at each path position, producing a 2D strip rather than a single line.
- The output xreal equals the physical path length (computed from pixel spacing), and yreal equals thickness times the pixel size.
- Bilinear interpolation (order=1) is used with nearest-edge boundary handling.
