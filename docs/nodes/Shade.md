# Shade

Render a DATA_FIELD as a directional hillshade image using Lambertian reflectance. Surface normals are estimated from Sobel gradients, and shading intensity is computed from the dot product with a configurable light direction. Equivalent to Gwyddion's `shade.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface field to shade |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| shaded | DATA_FIELD | Shaded surface rendering |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| azimuth | FLOAT | 0.0 | Light direction in degrees: 0 = north, 90 = east, 180 = south, 270 = west (0–360) |
| elevation | FLOAT | 45.0 | Light elevation angle above the horizon in degrees (0–90) |
| blend | FLOAT | 0.5 | Blend factor between original data and shading: 0.0 = original data only, 1.0 = shading only (0.0–1.0) |

## Notes

- Surface normals are computed using Sobel gradient operators, providing good noise resilience compared to simple finite differences.
- An azimuth of 315° (northwest illumination) is a common choice that produces natural-looking topographic shading.
- Elevation of 90° gives flat, uniform lighting; lower angles emphasize surface texture and fine features.
- The blend parameter controls how much shading modulates the original height data. Use 0.5 for a balanced view, or 1.0 for pure shaded relief.
