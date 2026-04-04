# Polynomial Distortion

Correct nonlinear scanner distortions by applying polynomial coordinate warping independently in the x and y directions. Each axis has three polynomial coefficients controlling linear, quadratic, and cubic distortion terms. Equivalent to Gwyddion's `polydistort.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with scanner distortion |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Distortion-corrected field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| k1_x | FLOAT | 0.0 | Linear distortion coefficient for the x axis (-1.0–1.0) |
| k2_x | FLOAT | 0.0 | Quadratic distortion coefficient for the x axis (-1.0–1.0) |
| k3_x | FLOAT | 0.0 | Cubic distortion coefficient for the x axis (-1.0–1.0) |
| k1_y | FLOAT | 0.0 | Linear distortion coefficient for the y axis (-1.0–1.0) |
| k2_y | FLOAT | 0.0 | Quadratic distortion coefficient for the y axis (-1.0–1.0) |
| k3_y | FLOAT | 0.0 | Cubic distortion coefficient for the y axis (-1.0–1.0) |

## Notes

- k1 controls linear stretching/compression, k2 controls barrel/pincushion-like quadratic distortion, and k3 controls cubic (S-shaped) distortion.
- Coefficients for x and y are independent, allowing correction of anisotropic scanner nonlinearities.
- Small values (0.01–0.1) are typical for real scanner corrections; large values produce extreme warping.
- Set all coefficients to 0.0 to pass the field through unchanged.
