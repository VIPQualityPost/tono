# Level Rotate

Level by physically rotating the data plane. Fits a best-fit plane, converts its slopes to tilt angles, then rotates the surface by those angles using interpolation rather than algebraic subtraction.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to level |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with tilt removed by rotation |
| tilt | RECORD_TABLE | Applied tilt angles X/Y in degrees |

## Notes

- Unlike Plane Level (which subtracts a fitted plane), this node rotates the 3D surface to make it horizontal. The distinction matters for steep tilts where subtraction introduces distortion.
- Uses bilinear interpolation to resample rotated z-values.
- Edges are handled with nearest-neighbor extension.
