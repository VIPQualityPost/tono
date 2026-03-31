# Cursors

Place two draggable cursors on a line plot or 2D field to measure positions and deltas. On lines it reports x/y positions and dx/dy; on fields it reports x/y/z at both markers plus dx/dy/dz.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| line | LINE or DATA_FIELD | Yes | Input line profile or 2D field |
| coord_pair | COORDPAIR | No | Locks both cursor positions from an external coordinate pair |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| measurement | RECORD_TABLE | Positions, deltas, and lengths at the two cursor locations |
| coord_pair | COORDPAIR | Current cursor positions (passthrough for chaining) |

## Controls

None (cursor positions are set by dragging in the preview panel).

## Limitations

- When a COORDPAIR is connected, the cursor positions are locked and cannot be dragged interactively.
- On 2D fields, z values are sampled with bilinear (order 1) interpolation.
