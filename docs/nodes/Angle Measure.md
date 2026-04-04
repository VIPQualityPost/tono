# Angle Measure

Measure the included angle between two draggable line segments over a DATA_FIELD or IMAGE. Drag either endpoint to change that arm, drag the middle joint to move the whole widget, and drag the angle label to reposition it.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input | ANNOTATION_SOURCE (DATA_FIELD or IMAGE) | Yes | Background image or field to annotate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| output | ANNOTATION_SOURCE | Input with the angle overlay attached |
| measurements | RECORD_TABLE | Angle in degrees, arm lengths, and arm/vertex coordinates |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| color | STRING (color picker) | #ff9800 | Overlay color for the angle arms and arc |
| stroke_width | FLOAT | 1.35 | Line thickness in display pixels (0.35-6.0) |

## Notes

- Coordinates are stored as fractions of the image dimensions; physical units depend on the input field's calibration.
- Angle measurement is the included angle at the vertex, always in [0°, 180°].
