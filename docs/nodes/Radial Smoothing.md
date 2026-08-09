# Radial Smoothing

Smooth an image in polar coordinates: the image is resampled around its center into a polar (radius, angle) grid, Gaussian-smoothed along the radial and/or angular direction, and mapped back.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to smooth |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| smoothed | DATA_FIELD | Polar-smoothed field with the same dimensions and physical extents as the input |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| sigma_r | FLOAT | 10.0 | Gaussian sigma along the radial direction, in pixels (0 disables radial smoothing) |
| sigma_phi_deg | FLOAT | 10.0 | Gaussian sigma along the angular direction, in degrees (0 disables angular smoothing) |
| interpolation | dropdown | linear | Interpolation used when resampling to and from polar coordinates: linear, cubic, or nearest |

## Notes

- The polar transform is centerd on pixel (xres/2, yres/2) of the input. The angular coordinate covers one full revolution in `ares = round(pi*max(xres,yres))` (rounded to an even number) steps; the radial coordinate has `rres = trunc(sqrt(xres^2+yres^2)/2)` bins, one per pixel of radius. The angular direction is periodically wrapped so the smoothing does not create a seam at 0/360 degrees.
- `sigma_r` blurs concentric circles (constant angle, values at different radii are averaged); `sigma_phi_deg` blurs along circles of constant radius (a rotational blur around the center). Setting either sigma to 0 disables that component; both can be applied at once.
- The Gaussian kernel is truncated at 5 sigma, exactly like separable row/column Gaussian smoothing.
- The workspace holds a polar array of about `2*ares*(rres+ares)` pixels, so memory use grows roughly linearly with image size times pi; very large images take correspondingly more memory.
