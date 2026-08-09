# PSF Estimation

Estimate a point spread function (PSF) from a measured (blurred) image and an ideal (sharp) reference. The estimated PSF can be fed into the Deconvolution node to restore other images acquired under the same conditions. Equivalent to Gwyddion's psf.c / psf-fit.c modules.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| measured | DATA_FIELD | Yes | Measured (blurred) image |
| ideal | DATA_FIELD | Yes | Ideal (sharp) reference image |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| psf | DATA_FIELD | Estimated point spread function |
| parameters | RECORD_TABLE | Fitted PSF parameters (sigma_x, sigma_y, amplitude); reported by all three methods |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | wiener | Estimation method: wiener, least_squares, or gaussian_fit |
| regularization | FLOAT | 0.01 | Regularization parameter (1e-6 to 1.0) |
| psf_size | INT | 32 | Size of the estimated PSF in pixels (4 to 128) |

## Notes

- **Wiener**: Pseudo-Wiener deconvolution in the frequency domain. Computes `conj(F_ideal) * F_measured / (|F_ideal|^2 + regularization)`. Fast and robust for most cases.
- **Least-squares**: Regularised frequency-domain division. Zeros out components where the ideal signal is too weak, avoiding noise amplification.
- Both Wiener and least-squares report the Gaussian fit (sigma_x, sigma_y, amplitude) of the estimated PSF in the parameters table, so all three methods return the same table layout.
- **Gaussian fit**: Estimates the PSF via the Wiener method, then fits a 2D Gaussian to the result using moment analysis. Returns the smooth fitted PSF and its parameters (sigma_x, sigma_y, amplitude). Useful when the PSF is known to be approximately Gaussian.
- The **regularization** parameter controls the noise/sharpness tradeoff. Smaller values yield sharper PSF estimates but amplify noise. Start with the default (0.01) and adjust if needed.
- The PSF output is always normalized to sum to 1 and cropped to `psf_size x psf_size` pixels centered on the peak.
- Connect the PSF output to the Deconvolution node for image restoration with the estimated kernel.
- Both input fields should have the same pixel dimensions for best results.
