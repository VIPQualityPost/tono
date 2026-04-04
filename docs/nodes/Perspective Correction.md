# Perspective Correction

Fix perspective distortion in a DATA_FIELD via a projective (homography) transform. Each corner can be shifted by a fractional offset to map a distorted quadrilateral back to a rectangle. Equivalent to Gwyddion's `correct_perspective.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with perspective distortion |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Perspective-corrected field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| top_left_x | FLOAT | 0.0 | Horizontal offset of the top-left corner as a fraction of image width (-0.5–0.5) |
| top_left_y | FLOAT | 0.0 | Vertical offset of the top-left corner as a fraction of image height (-0.5–0.5) |
| top_right_x | FLOAT | 0.0 | Horizontal offset of the top-right corner as a fraction of image width (-0.5–0.5) |
| top_right_y | FLOAT | 0.0 | Vertical offset of the top-right corner as a fraction of image height (-0.5–0.5) |
| bottom_left_x | FLOAT | 0.0 | Horizontal offset of the bottom-left corner as a fraction of image width (-0.5–0.5) |
| bottom_left_y | FLOAT | 0.0 | Vertical offset of the bottom-left corner as a fraction of image height (-0.5–0.5) |
| bottom_right_x | FLOAT | 0.0 | Horizontal offset of the bottom-right corner as a fraction of image width (-0.5–0.5) |
| bottom_right_y | FLOAT | 0.0 | Vertical offset of the bottom-right corner as a fraction of image height (-0.5–0.5) |

## Notes

- All offsets are given as fractions of the image dimensions (0.0 = no shift, 0.1 = 10% shift). Positive x shifts right, positive y shifts down.
- The transform uses bilinear interpolation to resample pixel values at non-integer locations.
- For trapezoidal distortions (common in tilted AFM scans), typically only two corners need adjustment.
- Set all offsets to 0.0 to pass the field through unchanged.
