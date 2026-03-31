# Save

Save a single value to disk. Supports fields, images, lines, tables, scalars, and 3D meshes. Does not auto-run; click Save to write.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| value | DATA_FIELD, IMAGE, ANNOTATION_SOURCE, LINE, RECORD_TABLE, DATA_TABLE, MESH_MODEL, or FLOAT | Yes | Value to save |
| directory | DIRECTORY | No | Optional directory path from a Folder node; overrides the directory_path widget |

## Outputs

None.

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| filename | STRING | "" | Output filename |
| directory_path | FOLDER_PICKER | "" | Output directory; hidden when directory input is connected |
| format | STRING (context-dependent) | TIFF | Output format; available choices depend on the connected input type |
| plot_title | STRING | "" | Optional title for line plots saved as PNG or TIFF |

## Limitations

- Available formats per input type: DATA_FIELD → TIFF, PNG, NPZ; IMAGE → PNG, TIFF, NPZ; LINE → PNG, TIFF, CSV, NPZ, JSON; RECORD_TABLE/DATA_TABLE → CSV, JSON; FLOAT → TXT, JSON; MESH_MODEL → OBJ, STL.
- divide-by-zero or NaN values in fields are preserved in TIFF/NPZ but may not render correctly in PNG.
