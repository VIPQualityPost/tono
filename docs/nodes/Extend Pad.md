# Extend Pad

Add configurable borders around a DATA_FIELD using various padding methods. Useful for preparing data for FFT-based operations that suffer from edge artifacts, or for aligning fields of different sizes. Equivalent to Gwyddion's `extend.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to pad |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| padded | DATA_FIELD | Field with added borders |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| left | INT | 0 | Number of pixels to add on the left edge (0-1024) |
| right | INT | 0 | Number of pixels to add on the right edge (0-1024) |
| top | INT | 0 | Number of pixels to add on the top edge (0-1024) |
| bottom | INT | 0 | Number of pixels to add on the bottom edge (0-1024) |
| method | dropdown | mirror | Padding method: mean (fill with field mean), edge (replicate border pixels), mirror (reflect across edge), periodic (tile the field), or zero (fill with zeros) |

## Notes

- Mirror and periodic padding avoid sharp discontinuities at the border and are recommended before FFT-based filtering.
- Edge padding replicates the outermost row/column of pixels into the border region.
- Zero padding fills borders with 0.0 and can introduce step artifacts; consider mean padding as an alternative.
- The output field's physical dimensions are extended proportionally to the added pixels.
