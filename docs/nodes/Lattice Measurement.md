# Lattice Measurement

Detect and measure periodic lattice structures from ACF or FFT peak positions. Reports lattice vectors and angles.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with periodic structure |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| correlation | DATA_FIELD | ACF or FFT magnitude used for detection |
| measurements | RECORD_TABLE | Detected lattice vectors, spacings, and angle |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | acf | Detection method: acf (autocorrelation) or fft (Fourier transform) |

## Notes

- ACF method finds the strongest off-center peaks in the 2D autocorrelation. Works well for real-space periodic structures.
- FFT method finds peaks in the power spectrum. Better for weak periodicity or noisy data.
- Reports up to two lattice vectors (a, b), their magnitudes, and the angle between them.
- For best results, the field should contain at least 3-4 complete periods in each direction.
