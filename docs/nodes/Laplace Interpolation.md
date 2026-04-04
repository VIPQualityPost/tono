# Laplace Interpolation

Fill masked (missing) regions by solving the Laplace equation with Dirichlet boundary conditions from surrounding pixels. Produces a smooth, harmonic interpolation without overshooting. Equivalent to Gwyddion's laplace.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with regions to fill |
| mask | IMAGE | Yes | Binary mask where white (255) marks pixels to interpolate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filled | DATA_FIELD | Field with masked regions filled by Laplace interpolation |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| iterations | INT | 500 | Number of Jacobi relaxation iterations; more iterations = smoother result (10-10000) |

## Notes

- Laplace interpolation produces the smoothest possible fill — it minimizes the integral of the squared gradient within the masked region.
- For small holes (<50 px diameter), 200-500 iterations is usually sufficient. Larger holes may need 1000+.
- Use a Draw Mask or Threshold Mask node to create the mask input.
- For surfaces with texture, consider Fractal Interpolation instead, which preserves surface roughness characteristics.
