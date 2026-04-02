# Draw Mask

Paint a binary mask directly over an image preview. Pen size controls newly drawn strokes, the Clear Mask button removes all strokes, and invert flips the final binary output.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Background field whose dimensions define the mask size |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask image (painted regions = white, background = black, or inverted) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| pen_size | INT | 12 | Brush diameter in pixels for newly drawn strokes (1–128) |
| invert | BOOLEAN | False | When enabled, swaps painted and unpainted regions |
| clear_mask | BUTTON | — | Clears all painted strokes |

## Notes

- Strokes are stored as path data; very long painting sessions with many strokes may accumulate large state.
- The mask resolution matches the input field resolution and cannot be changed independently.
