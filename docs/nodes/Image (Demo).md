# Image (Demo)

Load a bundled demo file so you can try the application without providing your own data. The file list is populated from the built-in demo directory at startup.

## Inputs

None.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Loaded demo field (first channel) |
| channel_2 | DATA_FIELD | Second channel, when the demo file has two or more channels |
| channel_3 | DATA_FIELD | Third channel, when the demo file has three or more channels |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| name | dropdown | (first demo file) | Name of the bundled demo file to load |
| colormap | dropdown | viridis | Colormap applied to the field; hidden when colormap_map is connected |

## Notes

- Only files present in the bundled demo directory are available; custom files cannot be added here.
- If no demo files are found, the dropdown shows "(no demo files found)".
