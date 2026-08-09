# Log-Polar PSDF

Compute the power spectral density function in log-polar coordinates. The x-axis is the azimuthal angle (0-360 degrees) and the y-axis is log(frequency). Better than Cartesian PSDF for anisotropy analysis.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input spatial-domain field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| psdf | DATA_FIELD | Power spectral density in log-polar coordinates (domain=frequency) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_phi | INT | 180 | Number of azimuthal angle bins (36-720) |
| n_r | INT | 100 | Number of radial (log-frequency) bins (20-500) |

## Notes

- The mean value is subtracted before computing the 2D FFT, and the power spectrum is shifted so DC is at the centre.
- Bilinear interpolation is used when sampling the Cartesian power spectrum onto the log-polar grid.
- The output is log-scaled via `log1p` for better visual contrast.
- Output xreal is 360.0 (degrees) and yreal is log(r_max) where r_max is half the shorter image dimension.
- Anisotropic surfaces produce bright bands at specific azimuthal angles; isotropic surfaces appear uniform along the angle axis.
