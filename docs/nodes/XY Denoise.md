# XY Denoise

Denoise a measurement acquired as two orthogonal scans (horizontal and vertical fast-scan directions), as in a standard XY Denoise workflow. The two fields are Fourier transformed; at every frequency the shared modulus is taken as the smaller of the two moduli and the phase comes from the horizontal scan — or the average of both phases when averaging is enabled. The inverse transform keeps only the component the two scans agree on, suppressing scan-direction noise and artefacts.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_x | DATA_FIELD | Yes | Measurement in the horizontal (x) scan direction |
| field_y | DATA_FIELD | Yes | Measurement of the same area in the orthogonal (y) scan direction |
| do_average | BOOLEAN | Yes | Average the phases of both scans instead of using the x-scan phase alone |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| denoised | DATA_FIELD | Denoised field, same resolution, extents and units as field_x |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| do_average | BOOLEAN | True | Average the cos/sin phase components of the two scans before reconstruction |

## Notes

- Both scans must have the same resolution, physical extent and units; the node raises an error otherwise (the same compatibility is required).
- With two identical scans the result reproduces the input exactly; with `do_average` off the reconstruction uses only the x-scan phase.
