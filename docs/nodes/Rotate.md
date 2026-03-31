# Rotate

Rotate a DATA_FIELD counterclockwise by an angle in degrees. Optionally expand the canvas to keep the full rotated field while preserving the field center.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to rotate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Rotated field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| angle | FLOAT | 90.0 | Rotation angle in degrees, counterclockwise (−360 to 360) |
| interpolation | dropdown | bilinear | Interpolation method for resampling: bilinear, nearest, or bicubic |
| expand_canvas | BOOLEAN | True | When True, canvas is expanded to contain the full rotated image; when False, canvas is clipped to original size |

## Limitations

- Rotation by angles other than multiples of 90° introduces interpolation artefacts.
- expand_canvas may produce fields with non-square pixel sizes for arbitrary angles.
