# Color Map

Build a reusable colormap. Choose a preset from the built-in palette list, or create a custom gradient with min/max colours and any number of intermediate stops.

## Inputs

None.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| colormap | COLORMAP | Colormap specification for use with other nodes |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | preset | Switch between preset and custom gradient modes |
| preset | dropdown | viridis | Built-in colormap preset name; visible when mode is preset |
| stops | STRING (colormap editor) | default gradient | JSON array of color stops for the custom gradient; visible when mode is custom |

## Notes

- Custom colormaps must include at least a minimum and maximum color stop.
- Stops must be valid JSON; invalid JSON will raise an error.
