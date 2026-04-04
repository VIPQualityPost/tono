# Calibration

Apply lateral and height calibration corrections to a DATA_FIELD. Equivalent to Gwyddion's calibrate.c functionality.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Data to calibrate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Calibrated field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| xy_mode | dropdown | keep | Lateral calibration mode: keep (no change), set_size (set explicit physical size), scale (multiply by factor) |
| z_mode | dropdown | keep | Height calibration mode: keep (no change), set_range (linear map to new min/max), scale (multiply by factor), offset (add constant) |
| xreal_new | float | 1e-6 | New x physical size (shown when xy_mode = set_size) |
| yreal_new | float | 1e-6 | New y physical size (shown when xy_mode = set_size) |
| xy_scale | float | 1.0 | Lateral scale factor (shown when xy_mode = scale) |
| z_min | float | 0.0 | New z minimum (shown when z_mode = set_range) |
| z_max | float | 1e-9 | New z maximum (shown when z_mode = set_range) |
| z_scale | float | 1.0 | Z scale factor (shown when z_mode = scale) |
| z_offset | float | 0.0 | Z offset value (shown when z_mode = offset) |
| xy_unit | string | (empty) | New XY unit string; leave empty to keep current |
| z_unit | string | (empty) | New Z unit string; leave empty to keep current |

## Notes

- Controls are conditionally shown based on the selected mode via show_when_widget_value.
- set_range linearly maps data from the current [min, max] to the specified [z_min, z_max]. If data is constant, z_min is applied uniformly.
- Unit fields accept any string (e.g. "m", "nm", "V"). An empty string preserves the existing unit.
