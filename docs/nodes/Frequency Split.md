# Frequency Split

Separate a DATA_FIELD into low-frequency and high-frequency components using an FFT-based Gaussian filter. The low-pass output contains smooth, large-scale variations while the high-pass output contains fine detail and noise. Equivalent to Gwyddion's `freq_split.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to split |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| low_pass | DATA_FIELD | Low-frequency (smoothed) component |
| high_pass | DATA_FIELD | High-frequency (detail) component |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| cutoff | FLOAT | 0.1 | Cutoff frequency as a fraction of Nyquist (0.001-0.5) |

## Notes

- The cutoff is relative to the Nyquist frequency. A value of 0.5 effectively passes everything (no filtering), while 0.001 aggressively removes nearly all spatial frequencies from the low-pass output.
- The two outputs always sum to the original field: low_pass + high_pass = input.
- Useful for separating roughness from waviness, or for removing long-range background while preserving features.
- The filter operates in the frequency domain via FFT, so it handles periodic boundaries naturally.
