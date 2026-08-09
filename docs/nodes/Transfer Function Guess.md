# Transfer Function Guess

Estimate the point spread / transfer function of an imaging system from a measured image and a known ideal response. The measured image is assumed to be the ideal response blurred by the instrument transfer function; the node recovers that transfer function by deconvolution. This mirrors the standard Transfer Function Guess workflow.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Measured (blurred) image |
| ideal | DATA_FIELD | Yes | Ideal, sharp response. Must have the same resolution and physical size as the measured image |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| psf | DATA_FIELD | Estimated transfer function / point spread function, cropped to the requested size and centered on its middle pixel |
| measurement | RECORD_TABLE | TF width, TF height (max absolute value), TF norm, difference norm between the measured image and the ideal re-convolved with the TF, and the regularization sigma used |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | regularised | Deconvolution method: regularised filter, pseudo-Wiener filter, or least squares on a small transfer-function support |
| sigma_log10 | FLOAT | 1.0 | Regularization parameter as log10; larger values give a smoother, more regularized transfer function |
| auto_sigma | BOOLEAN | False | Estimate the regularization sigma automatically by one-dimensional minimization of the transfer function width |
| txres | INT | 51 | Horizontal transfer function size in pixels (cropped for the regularised/wiener methods, support size for least squares) |
| tyres | INT | 51 | Vertical transfer function size in pixels |
| border | INT | 3 | Edge extension used by the least-squares method to suppress boundary errors |
| windowing | dropdown | welch | FFT window applied to both images before deconvolution to reduce edge effects |
| as_integral | BOOLEAN | True | Normalize as a convolution integral (continuous normalization); when off the TF is scaled to a discrete sum and its unit becomes dimensionless |

## Notes

- Both input fields should be windowed before processing; the windowing control applies the Welch (default), Hann, Hamming or Blackman window otherwise used implicitly by FFT-based methods.
- When as_integral is on, the transfer function is normalized as a continuous integral; convolving the ideal with it (as an integral) reproduces the measured image. With as_integral off, the values are scaled by the pixel area and the value unit becomes dimensionless.
- The transfer function width is measured as the dispersion of |PSF| inside the thresholded, central grain, following the width metric of psf.c.
- Images smaller than 24 pixels in either direction are rejected.
