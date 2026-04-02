# FFT Filter

Frequency-domain filtering of a line profile or 2D data field using a Butterworth transfer function. Connect a LINE for 1D filtering or a DATA_FIELD for 2D filtering; the output mirrors the input type. Equivalent to Gwyddion fft_filter_1d / fft_filter_2d.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input | LINE or DATA_FIELD | Yes | Input line or field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered | LINE or DATA_FIELD | Filtered output matching the input type |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| filter_type | dropdown | lowpass | Filter mode: lowpass, highpass, bandpass, or notch (band-reject) |
| cutoff | FLOAT | 0.1 | Lower cutoff frequency as a fraction of Nyquist (0.001–1.0) |
| cutoff_high | FLOAT | 0.4 | Upper cutoff for bandpass/notch modes (0.001–1.0) |
| order | INT | 2 | Butterworth filter order; higher values give steeper roll-off (1–10) |

## Notes

- cutoff_high is only used for bandpass and notch modes.
- The filter is applied in the frequency domain via FFT; very short lines may show wrap-around artefacts.
