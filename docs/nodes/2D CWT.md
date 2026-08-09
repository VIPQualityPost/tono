# 2D CWT

Compute the two-dimensional continuous wavelet transform (CWT) of a field and output the maximum wavelet response across a sweep of scales. The wavelet is applied in the Fourier domain, exactly as in Gwyddion's 2D CWT module (libprocess/cwt.c). A Gaussian wavelet is a scale-selective low-pass filter while the Mexican hat is a scale-selective band-pass; features whose lateral size matches a scale in the sweep produce a strong response at that scale.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to transform |
| wavelet | dropdown | Yes | Wavelet type: gaussian (GWY_2DCWT_GAUSS) or mexican_hat (GWY_2DCWT_HAT) |
| min_scale_px | FLOAT | Yes | Smallest wavelet scale in pixels (lower sweep bound) |
| max_scale_px | FLOAT | Yes | Largest wavelet scale in pixels (upper sweep bound) |
| n_scales | INT | Yes | Number of scales linearly spaced between the bounds |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| transform | DATA_FIELD | Maximum-over-scales absolute CWT response, same resolution and physical units as the input |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| wavelet | dropdown | mexican_hat | Selected 2D wavelet; Gwyddion distinguishes Gaussian and Hat types |
| min_scale_px | FLOAT | 2.0 | Smallest scale of the sweep, in pixels |
| max_scale_px | FLOAT | 20.0 | Largest scale of the sweep, in pixels |
| n_scales | INT | 10 | Number of scales in the sweep |

## Notes

- Scale is measured in pixels, matching Gwyddion's slider which can display the scale in pixel units.
- The Fourier-space wavelet `w(k) = exp(-s²k²/2)` (Gaussian) or `w(k) = s²k²·exp(-s²k²/2)·2πs²` (Mexican hat) is sampled on the raw-FFT frequency grid with radial frequency `mval = 4·|k|/xres`, as in `gwy_cwt_wfunc_2d()` and `gwy_data_field_mult_wav()`.
- Gwyddion's interactive dialog shows the single-scale CWT as the scale slider is swept; this node freezes that behaviour into one output field by taking the element-wise maximum of the absolute single-scale responses.
- The Gaussian wavelet does not suppress zero frequency, so a constant background appears in its response; the Mexican hat (and subtracting the mean) removes it.
- Physical units of the output equal those of the input.
