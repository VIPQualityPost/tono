# Mask Shift

Translate a binary mask by an integer pixel offset. Choose how out-of-bounds regions are filled: zero (empty), wrap (periodic roll), or mirror (reflected padding). Equivalent to Gwyddion's mask_shift.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mask | IMAGE | Yes | Binary mask to shift |
| field | DATA_FIELD | No | Optional field for preview background display |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Shifted binary mask |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| shift_x | INT | 0 | Horizontal shift in pixels (-1000 to 1000). Positive values shift right. |
| shift_y | INT | 0 | Vertical shift in pixels (-1000 to 1000). Positive values shift down. |
| border_mode | dropdown | zero | How to handle edges: zero fills vacated region with empty mask, wrap rolls periodically, mirror reflects at boundaries |

## Notes

- Shift values are in pixels, not physical units.
- **zero** mode: the mask is rolled and the vacated strip is cleared to zero (unmasked). Useful when the shifted region should not wrap around.
- **wrap** mode: uses periodic rolling (`np.roll`). The total number of masked pixels is preserved. Suitable for periodic or tiled data.
- **mirror** mode: pads with reflected values before cropping, so edges are filled with a mirrored copy of the mask boundary. Avoids hard cutoffs at the border.
