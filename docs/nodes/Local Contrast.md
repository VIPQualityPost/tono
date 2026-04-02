# Local Contrast

Expand the local dynamic range at each pixel to reveal fine surface features that are hidden by global contrast range. Equivalent to Gwyddion local_contrast.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Field with enhanced local contrast |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| kernel_size | INT | 10 | Size of the local neighbourhood window in pixels (2–100) |
| weight | FLOAT | 0.5 | Blend weight between original and full-contrast output (0 = original, 1 = full local contrast; 0–1) |

## Notes

- Large kernel sizes are slow; values above ~50 pixels may be noticeably slow on large fields.
- The enhancement is purely a display-contrast operation; it changes the underlying data values.
