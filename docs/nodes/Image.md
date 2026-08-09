# Image

Load any supported file. SPM formats (.gwy, .sxm, .ibw) and HDF5 (.h5, .hdf5) provide calibrated dimensions; up to three channels are exposed as separate outputs. Images (.png, .tiff, .jpg) and arrays (.npy, .npz) are loaded as uncalibrated fields.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | FILE_PATH | No | File path input from a Folder node or other path source; overrides the filename widget |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| path | FILE_PATH | Resolved absolute file path |
| field | DATA_FIELD | Loaded data field (first channel) |
| channel_2 | DATA_FIELD | Second channel, when the file has two or more channels |
| channel_3 | DATA_FIELD | Third channel, when the file has three or more channels |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| filename | FILE_PICKER | "" | Path to the file to load; hidden when path input is connected |
| colormap | dropdown | viridis | Colormap applied to the loaded field; hidden when colormap_map is connected |

## Notes

- Uncalibrated formats (images, arrays) emit a warning and produce fields without physical dimensions.
- Multi-channel files (e.g. .gwy with multiple data channels) expose up to three channels on the channel_2/channel_3 outputs; further channels are dropped with a warning.
