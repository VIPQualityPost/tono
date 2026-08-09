# Merge

Merge three data fields into a single RGB image. Each channel is scaled to 0..255 — automatically over its own full data range, or manually with a user-provided offset and scale — and then combined as the red, green and blue channels of the output image.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| red | DATA_FIELD | Yes | Channel placed in the red plane |
| green | DATA_FIELD | Yes | Channel placed in the green plane |
| blue | DATA_FIELD | Yes | Channel placed in the blue plane |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| image | IMAGE | RGB composite image, uint8 array of shape (H, W, 3) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| scaling | dropdown | auto | Channel scaling: auto stretches each channel's full data range to 0..255; manual maps (value - offset) / scale to 0..255 |
| offset | FLOAT | 0.0 | Manual mode: value mapped to channel level 0 |
| scale | FLOAT | 1.0 | Manual mode: value span mapped to the full 0..255 range (must be positive) |

## Notes

- All three channels must have identical resolution; otherwise the node raises an error.
- In auto mode each channel is normalised independently, so a flat channel becomes 0 (black).
- In manual mode values outside [offset, offset + scale] are clipped to 0 or 255.
- The input fields may carry different physical units; scaling converts them to the display range of the composite image.
