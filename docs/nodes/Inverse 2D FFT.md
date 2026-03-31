# Inverse 2D FFT

Reconstruct a spatial-domain image from a 2D frequency spectrum. For exact reconstruction, connect magnitude/phase (or log magnitude/phase, or PSDF/phase) from the 2D FFT node. If phase is omitted, zero phase is assumed.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| spectrum | DATA_FIELD | Yes | Frequency-domain field (output of FFT 2D) |
| phase | DATA_FIELD | No | Phase field; if omitted, zero phase is used |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| image | DATA_FIELD | Reconstructed spatial-domain field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| representation | dropdown | magnitude | How to interpret the spectrum input: magnitude, log_magnitude, or psdf |

## Limitations

- The spectrum input must be a frequency-domain DATA_FIELD; connecting a spatial-domain field raises an error.
- If phase is connected, it must also be a frequency-domain field with the same shape as the spectrum.
- Reconstruction from PSDF (which discards phase) assumes zero phase and produces a symmetric result.
