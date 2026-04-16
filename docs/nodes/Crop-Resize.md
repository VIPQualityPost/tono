# Crop / Resize

Crop a DATA_FIELD with a draggable rectangle defined by two corners, then optionally resize it. Cropping updates physical extents and offsets; resizing preserves the cropped physical size.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to crop |
| corner_a | COORD | No | Locks the top-left corner of the crop box |
| corner_b | COORD | No | Locks the bottom-right corner of the crop box |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Cropped (and optionally resampled) field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| target_width | INT | 0 | Output pixel width after resampling (0 = keep cropped width) |
| target_height | INT | 0 | Output pixel height after resampling (0 = keep cropped height) |
| interpolation | dropdown | bilinear | Resampling interpolation: bilinear, nearest, or bicubic |
| square | BOOLEAN | False | If true, the crop region is constrained to a physical square (longer side shrinks to match shorter). The on-preview rectangle also snaps to square while dragging either corner. |

## Notes

- The crop region must have non-zero width and height; an error is raised otherwise.
- If only one of target_width or target_height is set, the other dimension is computed to preserve aspect ratio.
- Physical extents are scaled proportionally when resampling.
- With `square` enabled, the side length is chosen in physical units (using the field's `xreal`/`yreal`), so the cropped region looks square on the preview for fields with square pixels.
