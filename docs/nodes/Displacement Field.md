# Displacement Field

Distort an image using synthetic displacement fields. Supports correlated Gaussian noise and tear-line distortion modes. Equivalent to Gwyddion's displfield.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to distort |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Distorted field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | gaussian_1d | Distortion method: gaussian_1d, gaussian_2d, or tear |
| sigma | float | 5.0 | Distortion amplitude in pixels |
| tau | float | 20.0 | Lateral correlation length in pixels |
| density | float | 0.02 | Tear density — fraction of rows that become tear lines (tear mode only) |
| seed | int | 42 | Random seed for reproducibility |

## Notes

- **gaussian_1d** generates a 1D correlated random displacement applied only in the x direction. All rows share the same displacement profile, simulating a systematic lateral distortion.
- **gaussian_2d** generates independent 2D correlated random displacements in both x and y. This produces a more general warping of the image.
- **tear** mode simulates scanning artifacts where random horizontal tear lines introduce sudden x-offsets that decay exponentially away from the tear row. This is useful for simulating or studying piezo slip artifacts in SPM data.
- The **sigma** parameter controls the magnitude of the displacement. Larger values produce more extreme distortion.
- The **tau** parameter controls the spatial correlation length. A larger tau produces smoother, more slowly varying displacement fields. The ratio sigma/tau roughly determines the local strain.
- For realistic scanning artifacts, use tear mode with low density (0.01--0.05) and moderate sigma.
