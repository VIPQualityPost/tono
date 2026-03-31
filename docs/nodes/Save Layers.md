# Save Layers

Save one or more image/field layers to a single file. Each layer input accepts either a DATA_FIELD or an IMAGE, including annotated images. Use this for composing multi-channel stacks. Does not auto-run; click Save to write.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| directory | DIRECTORY | No | Optional directory path from a Folder node; overrides the directory_path widget |
| field_0 … field_N | DATA_FIELD, IMAGE, or ANNOTATION_SOURCE | No | Layer inputs; a new slot appears as each one is filled |

## Outputs

None.

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| filename | STRING | "" | Output filename (without directory); used together with directory_path |
| directory_path | FOLDER_PICKER | "" | Output directory; hidden when directory input is connected |
| format | dropdown | TIFF | Output format: TIFF (multi-page, float32 for fields) or NPZ (named arrays) |
| layer_name_0 … layer_name_N | STRING | "" | Optional name for each layer; used as TIFF page descriptions or NPZ array keys |

## Limitations

- At least one layer must be connected; an error is raised otherwise.
- TIFF writes DATA_FIELD layers as float32; IMAGE layers are written as uint8.
- NPZ keys are sanitized to valid Python identifiers; duplicate names are made unique with numeric suffixes.
