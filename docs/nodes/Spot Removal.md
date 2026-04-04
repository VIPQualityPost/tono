# Spot Removal

Fill defect pixels (hot pixels, dropouts, scan artifacts) by interpolation. The mask defines defect locations. Equivalent to Gwyddion spotremove.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with defect pixels |
| mask | IMAGE | No | Binary mask marking defect pixel locations; if omitted, no inpainting is performed |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Field with defect pixels replaced by interpolated values |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | laplace | Inpainting method: laplace (smooth Laplace equation solution), mean (local mean), or zero |
| max_iter | INT | 100 | Maximum number of iterations for the Laplace solver (1-2000) |

## Notes

- Large masked regions may not converge fully within max_iter iterations using the Laplace method.
- The mean method uses a simple neighbourhood average and may leave visible discontinuities at large defect clusters.
