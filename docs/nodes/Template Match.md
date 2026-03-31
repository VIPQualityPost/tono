# Template Match

Find a template pattern within a larger data field using normalised cross-correlation. The score output shows match quality (1 = perfect match). Equivalent to Gwyddion maskcor.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| image | DATA_FIELD | Yes | Larger field to search in |
| template | DATA_FIELD | Yes | Smaller template pattern to find |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| score | DATA_FIELD | Normalized cross-correlation score map |
| detections | IMAGE | Binary mask marking positions above the threshold |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| threshold | FLOAT | 0.8 | Minimum correlation score to mark as a detection (0.0–1.0) |

## Limitations

- The template must be smaller than the image; equal or larger sizes are not supported.
- Normalized cross-correlation assumes uniform background; strong global gradients reduce detection accuracy.
