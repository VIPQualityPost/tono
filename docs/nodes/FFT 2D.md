# FFT 2D

Compute the 2D FFT with optional windowing and mean/plane subtraction. Outputs log magnitude, magnitude, phase, and PSDF as separate channels. Equivalent to gwy_data_field_2dfft / gwy_data_field_2dpsdf.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input spatial-domain field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| log_magnitude | DATA_FIELD | log(1 + |F|) of the 2D FFT, centered on DC |
| magnitude | DATA_FIELD | |F| of the 2D FFT, centered on DC |
| phase | DATA_FIELD | Phase angle of the 2D FFT in radians, centered on DC |
| psdf | DATA_FIELD | 2D power spectral density function |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| windowing | dropdown | hann | Window function applied before FFT: hann, hamming, blackman, or none |
| level | dropdown | mean | Pre-processing: subtract mean, subtract plane, or none |

## Notes

- Output fields are in the frequency domain; physical units on axes are spatial frequency (1/m).
- Phase output uses the raw FFT phase and is sensitive to field origin; it is most useful when paired with the Inverse 2D FFT node.
