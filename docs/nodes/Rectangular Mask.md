# Rectangular Mask

Create a binary mask covering a rectangular region of a DATA_FIELD. Useful when you want to select a region of interest for downstream nodes (statistics, flattening, masking operators) without cropping the image.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |
| corner_a | COORD | No | Locks corner A from an external coordinate |
| corner_b | COORD | No | Locks corner B from an external coordinate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask (255 inside the rectangle, 0 outside) matching the input field's pixel resolution |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| square | BOOLEAN | False | If true, the mask is coerced to a physical square — the longer side is shrunk to match the shorter, anchored at the top-left corner |
| invert | BOOLEAN | False | If true, the mask covers everything outside the rectangle instead of inside |

## Interactive preview

The node renders the input field with a draggable rectangle. Drag corner A or B to resize; drag inside the box to move it. Incoming COORD inputs lock the corresponding corner so it can't be moved interactively.

## Notes

- The output mask has the same resolution (xres × yres) as the input field.
- Pixel boundaries are chosen to fully contain the selected rectangle (floor on the low corner, ceil on the high corner).
- With `square` enabled, the side length is chosen in physical units (using `xreal`/`yreal`), so the mask looks square on the preview for fields with square pixels. For non-square pixels it is physically square but may render as a rectangle pixel-wise.
