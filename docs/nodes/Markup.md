# Markup

Draw simple vector shapes (lines, rectangles, circles, arrows) over a DATA_FIELD or IMAGE without flattening the raw data. Shapes are drawn interactively in the preview panel.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input | ANNOTATION_SOURCE (DATA_FIELD or IMAGE) | Yes | Background image or field to annotate |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| output | ANNOTATION_SOURCE | Input with vector markup overlay attached |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| shape | dropdown | arrow | Shape type to draw next: line, rectangle, circle, or arrow |
| stroke_color | STRING (color picker) | #ff0000 | Color for newly drawn shapes |
| stroke_width | INT | 3 | Line thickness in display pixels for newly drawn shapes (1-64) |
| clear_shapes | BUTTON | — | Remove all drawn shapes |

## Notes

- Shapes are stored as fractional coordinates; physical positions depend on field calibration.
- Individual shape properties (color, width) cannot be changed after drawing; use Clear Shapes to start over.
