# Perspective Correction

Fix perspective distortion in a DATA_FIELD via a projective (homography) transform. Each corner can be shifted by a fractional offset to map a distorted quadrilateral back to a rectangle.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with perspective distortion |
| top_left | COORD | No | Override top-left corner offset (x, y) |
| top_right | COORD | No | Override top-right corner offset (x, y) |
| bottom_left | COORD | No | Override bottom-left corner offset (x, y) |
| bottom_right | COORD | No | Override bottom-right corner offset (x, y) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Perspective-corrected field |

## Interactive preview

The preview shows the source image with a draggable quadrilateral overlay. Drag any corner handle to adjust the perspective correction. Use the Source/Corrected tabs to switch between the input image (with handles) and the corrected result.

Corner positions can also be set by connecting Coordinate nodes to the optional COORD inputs, which override the handle-driven values.

## Notes

- All offsets are given as fractions of the image dimensions (0.0 = no shift, 0.1 = 10% shift). Positive x shifts right, positive y shifts down.
- The transform uses bilinear interpolation to resample pixel values at non-integer locations.
- For trapezoidal distortions (common in tilted AFM scans), typically only two corners need adjustment.
- When all offsets are zero (default), the field passes through unchanged.
