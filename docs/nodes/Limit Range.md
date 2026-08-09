# Limit Range

Limit the value range of a DATA_FIELD using lower and upper thresholds. Clip mode is equivalent to Gwyddion's "Limit Range" process (module `threshold.c`) with the thresholds method: values are clamped into the range via `gwy_data_field_clamp`.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to limit |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Field with values limited to the target range |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| low | FLOAT | 0.0 | Lower bound of the target range |
| high | FLOAT | 1.0 | Upper bound of the target range |
| mode | dropdown | clip | clip: clamp values into [min(low,high), max(low,high)]; scale: clamp, then linearly map low to 0 and high to 1 |

## Notes

- As in Gwyddion, low and high are interchangeable: the range is always [min(low, high), max(low, high)].
- Clip mode is a pure clamp (`gwy_data_field_clamp` semantics) and leaves the physical metadata untouched.
- Scale mode is a tono extension beyond Gwyddion (Gwyddion only clamps); it compresses the clamped range to [0, 1] with `(value - low) / (high - low)`. It requires low != high and raises ValueError otherwise.
- Useful for cutting off outliers or preparing data for display/export with a known value range.
