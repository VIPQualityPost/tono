# Periodic Translate

Move data in the horizontal plane, treating it as periodic: pixels that leave one side of the image reappear on the opposite side, so the data wraps around. Equivalent to Gwyddion's ptranslate module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to translate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| translated | DATA_FIELD | Periodically translated field (same shape and physical extents) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| dx | INT | 0 | Move-by amount in the x direction, in pixels (positive moves the image content right) |
| dy | INT | 0 | Move-by amount in the y direction, in pixels (positive moves the image content down) |
| update_offsets | BOOLEAN | False | Also update the coordinate offsets so features keep their physical positions (Gwyddion's "Update coordinate offsets") |

## Notes

- The data is rolled: content shifted out on one edge is re-inserted on the opposite edge; nothing is lost or filled.
- When `update_offsets` is enabled the offsets are wrapped the same way Gwyddion stores them (into the [-real/2, real/2) range) after adding the shift, so the same physical location continues to show the same content. With it disabled the offsets are preserved unchanged.
- Equals Gwyddion `ptranslate.c` (`gwy_data_field_translate_periodically` + `update_offset`), ported to numpy `roll`.
