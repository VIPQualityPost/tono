# MFM Domain Generation

Generate the stray field from a periodic pattern of parallel magnetic stripe domains with alternating up/down magnetization.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Topography used for grid dimensions |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| hz | DATA_FIELD | z-component of the stray field (A/m) |
| dhz_dz | DATA_FIELD | Vertical gradient of the stray field (A/m²) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| height | FLOAT | 50e-9 | Tip-sample separation in metres |
| thickness | FLOAT | 20e-9 | Magnetic film thickness in metres |
| magnetization | FLOAT | 1e6 | Saturation magnetization in A/m |
| stripe_width_a | FLOAT | 200e-9 | Width of the A (+M) domain in metres |
| stripe_width_b | FLOAT | 200e-9 | Width of the B (-M) domain in metres |
| gap | FLOAT | 0.0 | Domain wall gap between stripes in metres |

## Notes

- Domains alternate between A (+M, magnetization up) and B (-M, magnetization down) with an optional gap of zero magnetization between them.
- The stray field is computed via FFT of the magnetization profile using an exponential decay transfer function.
- The field is uniform along y; stripes run parallel to the y-axis.
- dHz/dz is proportional to the MFM phase signal (force gradient), making it the quantity most directly comparable to raw MFM images.
- Useful for simulating MFM calibration samples and testing MFM analysis workflows.
- Typical stripe widths range from 100 nm to several microns.
