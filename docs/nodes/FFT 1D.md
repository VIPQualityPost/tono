# FFT 1D

Compute the FFT amplitude spectrum of a line profile and identify the dominant period. The output x-axis is period (not frequency), sorted from short to long.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| profile | LINE | Yes | Input line profile |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| frequency_plot | LINE | FFT amplitude spectrum vs. period |
| max | RECORD_TABLE | Table with the peak period |

## Controls

None.

## Notes

- The DC component is excluded from the output.
- Spectrum is one-sided (real FFT); the x-axis shows period, not frequency.
- No windowing is applied; spectral leakage may affect results on non-periodic inputs.
