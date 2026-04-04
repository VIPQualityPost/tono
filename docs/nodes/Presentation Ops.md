# Presentation Ops

Manage presentation overlays on data fields. Provides logarithmic scaling, normalisation extraction, overlay attachment, and linear blending. Equivalent to Gwyddion's `presentationops.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Primary data field |
| overlay | DATA_FIELD | No | Field to attach or blend as an overlay (used by attach and blend modes) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Processed data field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | logscale | Operation mode: logscale, extract_presentation, attach, or blend |
| blend_factor | FLOAT | 0.5 | Linear blend ratio between field (0.0) and overlay (1.0); only shown in blend mode (0.0--1.0) |

## Notes

- **logscale**: Shifts the data so the minimum becomes a small positive value, then applies log10. Useful for data with large dynamic range such as power spectral densities or FFT magnitudes.
- **extract_presentation**: Normalises the field to the [0, 1] range. Handy for generating a quick visual overview or feeding into colour-mapping nodes.
- **attach**: Replaces the field data with the overlay data. If the overlay has different dimensions it is resampled with cubic interpolation to match.
- **blend**: Linearly mixes `(1 - blend_factor) * field + blend_factor * overlay`. The overlay is resampled if its dimensions differ from the field.
- Overlay resampling uses `scipy.ndimage.zoom` with third-order (cubic) interpolation.
