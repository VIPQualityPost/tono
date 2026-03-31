# Annotations

Attach optional publication-style annotations (scale bar, color-map legend) to a DATA_FIELD without flattening the raw data, or annotate an IMAGE that carries viewport metadata from View3D.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input | ANNOTATION_SOURCE (DATA_FIELD or IMAGE) | Yes | Field or image to annotate |
| colormap_map | COLORMAP | No | Colormap socket; overrides the colormap widget |
| font | FONT | No | Font specification for annotation text |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| output | ANNOTATION_SOURCE | Input with annotation overlay attached |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| colormap | dropdown | auto | Colormap for the legend; hidden when colormap_map is connected |
| show_scale_bar | BOOLEAN | True | Render a physical scale bar |
| show_color_map | BOOLEAN | True | Render a color-map legend with min/mid/max values |
| text_size | FLOAT | 14.0 | Font size in points for annotation labels (6–96) |

## Limitations

- Scale bar and color-map legend require the input to carry physical dimension and unit metadata; plain images without metadata will emit a warning and the feature will be skipped.
