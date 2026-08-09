# Wavelet Denoise

Denoise a DATA_FIELD using wavelet coefficient thresholding. BayesShrink adapts the threshold per sub-band; VisuShrink uses a global threshold. Equivalent to applying a DWT with coefficient thresholding.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to denoise |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| denoised | DATA_FIELD | Denoised field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| wavelet | dropdown | db4 | Wavelet family: db1 (Haar), db2, db4, db8, sym4, coif1, or bior1.3 |
| method | dropdown | BayesShrink | Threshold estimation method: BayesShrink (per sub-band adaptive) or VisuShrink (global universal) |
| sigma | FLOAT | 0.0 | Noise level estimate in data units; 0 = automatic estimation (0-1.0) |
| mode | dropdown | soft | Thresholding mode: soft (smooth shrinkage) or hard (zero below threshold) |

## Notes

- The field size should ideally be a power of two for best wavelet decomposition; other sizes are handled by padding.
- sigma = 0 triggers automatic noise estimation from the finest-scale wavelet coefficients; this may be inaccurate on strongly structured surfaces.
