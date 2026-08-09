# Deconvolution

Restore an image via regularised deconvolution. Assumes the image was blurred by a Gaussian PSF with the given sigma.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input blurred field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| restored | DATA_FIELD | Deconvolved (sharpened) field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | wiener | Deconvolution method: wiener or richardson_lucy |
| sigma | FLOAT | 2.0 | Gaussian PSF sigma in pixels (0.1-50.0) |
| regularisation | FLOAT | 0.01 | Regularisation parameter for Wiener filter (1e-6-1.0) |
| iterations | INT | 10 | Number of iterations (Richardson-Lucy only, 1-200) |

## Notes

- **Wiener**: Fast, single-pass frequency-domain filter. The regularisation parameter controls the noise/sharpness tradeoff — smaller values sharpen more but amplify noise.
- **Richardson-Lucy**: Iterative method that preserves positivity. More iterations = sharper result but risk of ringing artifacts.
- The PSF sigma should match the actual blur in the image. If unknown, start with sigma=1-3 and adjust.
- For tip-shape deconvolution (non-Gaussian PSF), use Tip Deconvolution instead.
