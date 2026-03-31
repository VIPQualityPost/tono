# Preview

Display an IMAGE or DATA_FIELD as a coloured thumbnail in the node panel.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input | ANNOTATION_SOURCE (DATA_FIELD or IMAGE) | No | Field or image to display |
| colormap_map | COLORMAP | No | Colormap socket; overrides the colormap widget |

## Outputs

None.

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| colormap | dropdown | auto | Colormap used when rendering a DATA_FIELD or grayscale IMAGE; hidden when colormap_map is connected |

## Limitations

- When no input is connected, an error is raised at execution time.
- Connecting a FILE_PATH socket (instead of DATA_FIELD) raises a type error; ensure the correct socket is connected.
