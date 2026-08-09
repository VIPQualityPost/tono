# Null Offsets

Set the physical offsets (xoff, yoff) of a DATA_FIELD to zero. Equivalent to Gwyddion's `null_offsets` basic operation (module `basicops.c`), which calls `gwy_data_field_set_xoffset`/`set_yoffset` with 0.0.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field whose offsets should be nulled |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Field with xoff = 0 and yoff = 0, data unchanged |

## Controls

_None._

## Notes

- The data values are not modified — only the position metadata changes.
- The physical origin therefore moves to the upper-left corner of the field: after this operation the upper-left pixel is at (0, 0) in physical coordinates.
- Physical extents (xreal, yreal) and units are preserved.
