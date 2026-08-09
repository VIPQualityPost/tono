# Mask Noisify

Add random noise to a binary mask by flipping pixels near boundaries.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mask | IMAGE | Yes | Binary mask to perturb |
| field | DATA_FIELD | No | Optional field for preview background display |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Noisified binary mask |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| density | FLOAT | 0.1 | Fraction of candidate pixels to flip (0.0--1.0) |
| direction | dropdown | both | Which pixels to perturb: add (grow mask), remove (shrink mask), or both |
| boundaries_only | BOOLEAN | True | Only modify pixels adjacent to a mask boundary |
| seed | INT | 42 | Random seed for reproducible results (0--999999) |

## Notes

- Boundary detection uses four-neighbor comparison (up, down, left, right) via np.roll. A pixel is a boundary pixel if it differs from at least one of its four neighbors.
- Direction modes control which candidates are eligible: "add" selects only unmasked boundary pixels, "remove" selects only masked boundary pixels, and "both" selects all boundary pixels.
- Setting boundaries_only to False allows any pixel in the mask to be a candidate, not just those at edges.
- The seed parameter ensures deterministic output for a given input, which is useful for repeatable experiments.
