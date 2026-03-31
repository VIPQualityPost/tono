# Coordinate

Output a fractional (x, y) coordinate pair in [0, 1] for use with Cross Section, Cursors, or other nodes that accept a COORD input.

## Inputs

None.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| point | COORD | Fractional (x, y) coordinate |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| x | FLOAT | 0.5 | Horizontal position as a fraction of image width (0 = left, 1 = right) |
| y | FLOAT | 0.5 | Vertical position as a fraction of image height (0 = top, 1 = bottom) |

## Limitations

- Values are clamped to [0, 1] by downstream nodes; this node does not enforce clamping itself.
