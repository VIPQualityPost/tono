# Gradient

Compute the spatial gradient using a Sobel operator. Outputs the gradient magnitude, x-component, y-component, or azimuthal direction.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| gradient | DATA_FIELD | Gradient output in the selected component |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| component | dropdown | magnitude | Output component: magnitude (√(gx²+gy²)), x (horizontal gradient), y (vertical gradient), or azimuth (angle in degrees) |

## Notes

- Gradient components are in units of z_unit/xy_unit; azimuth is in degrees.
- Sobel operator uses a 3×3 kernel; sub-pixel features smaller than one pixel cannot be resolved.
