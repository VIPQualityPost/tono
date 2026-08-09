# PSDF

Compute the two-dimensional power spectral density function with window RMS compensation and centered zero frequency.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input spatial-domain field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| psdf | DATA_FIELD | 2D power spectral density, centered on DC |
| measurement | RECORD_TABLE | Total RMS roughness recovered from the PSD (Parseval-consistent) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| windowing | dropdown | hann | Window function applied before FFT to reduce spectral leakage: hann, hamming, blackman, or none |
| level | dropdown | mean | Pre-processing: subtract mean, subtract plane, or none |

## Notes

- Output is in the frequency domain; physical units on axes are spatial frequency (1/m) and PSDF units are z_unit²·m².
- Window RMS compensation is applied to normalize the spectral density consistently across window choices.
