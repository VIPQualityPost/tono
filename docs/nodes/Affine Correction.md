# Affine Correction

Fix geometric distortions from scanner nonlinearity by applying an affine transformation. Corrects shear, anisotropic scaling, and rotation.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with geometric distortion |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Affine-corrected field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| shear_x | FLOAT | 0.0 | Horizontal shear factor |
| shear_y | FLOAT | 0.0 | Vertical shear factor |
| scale_x | FLOAT | 1.0 | Horizontal scale factor |
| scale_y | FLOAT | 1.0 | Vertical scale factor |
| angle | FLOAT | 0.0 | Rotation angle in degrees |

## Notes

- An identity transform (shear=0, scale=1, angle=0) returns the original data unchanged.
- The output shape matches the input; pixels outside the transformed region are filled by nearest-edge interpolation.
- For simple rotation without scaling/shear, use the Rotate node instead.
