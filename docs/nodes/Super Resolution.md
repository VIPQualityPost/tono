# Super Resolution

Combine multiple aligned scans to produce a super-resolved image with higher spatial resolution. Sub-pixel shifts between inputs are estimated via FFT cross-correlation and used to reconstruct a finer grid.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field1 | DATA_FIELD | Yes | Reference image |
| field2 | DATA_FIELD | No | Second image |
| field3 | DATA_FIELD | No | Third image |
| field4 | DATA_FIELD | No | Fourth image |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Super-resolved image |
| alignment | RECORD_TABLE | Per-frame sub-pixel shifts (px and physical units) relative to the reference |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| upscale | INT | 2 | Upscaling factor (2, 3, or 4) |

## Notes

- When only one field is provided the image is upsampled using cubic interpolation (no multi-image enhancement).
- Additional fields are aligned to the reference using FFT-based cross-correlation with parabolic sub-pixel refinement, then averaged on the high-resolution grid.
- Providing more images generally improves the result because each scan samples slightly different sub-pixel positions.
- All input fields should have the same pixel dimensions and physical size for correct alignment.
- The upscale factor controls the output resolution multiplier (2x, 3x, or 4x the input dimensions).
