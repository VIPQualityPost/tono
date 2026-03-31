# Fractal Dimension

Calculate the surface fractal dimension using Gwyddion's partitioning, cube counting, triangulation, power-spectrum, or HHCF methods. The in-node graph shows the log-log curve and allows dragging the fit range.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| dimension | FLOAT | Estimated fractal dimension |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | partitioning | Algorithm: partitioning, cube_counting, triangulation, psdf (power spectrum), or hhcf (structure function) |
| interpolation | dropdown | linear | Interpolation used when resampling the field to a square grid: linear, nearest, or cubic |

## Limitations

- The field is resampled to a square grid internally; highly anisotropic scan sizes may introduce interpolation artefacts.
- Fit range can be adjusted interactively on the log-log plot; the default range covers the full data.
