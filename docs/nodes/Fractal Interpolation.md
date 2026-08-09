# Fractal Interpolation

Fill masked regions using fractal interpolation. Matches the spectral characteristics of the surrounding surface to produce natural-looking infill that preserves texture. Better than Laplace for rough surfaces.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with regions to fill |
| mask | IMAGE | Yes | Binary mask where white (255) marks pixels to interpolate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filled | DATA_FIELD | Field with masked regions filled by fractal interpolation |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| iterations | INT | 200 | Number of boundary relaxation iterations (10-5000) |

## Notes

- Fractal interpolation synthesizes fill data whose power spectrum matches the surrounding surface. This produces a more realistic appearance than Laplace interpolation for textured or rough surfaces.
- The fill region boundaries are smoothed via relaxation to ensure continuity.
- For very smooth surfaces, Laplace Interpolation may produce cleaner results.
- The seed for random synthesis is fixed for reproducibility.
