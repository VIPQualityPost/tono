# Coordinate Pair

Combine two COORD values into a single COORDPAIR for use with nodes that accept a line segment or marker pair input.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| a | COORD | Yes | First coordinate (x, y) in fractional [0, 1] units |
| b | COORD | Yes | Second coordinate (x, y) in fractional [0, 1] units |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| coord_pair | COORDPAIR | Pair of coordinates as a single value |

## Controls

None.

## Notes

- Coordinates are expected to be in the [0, 1] fractional range; values outside this range may produce unexpected results in downstream nodes.
