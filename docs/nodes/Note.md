# Note

Read the Note metadata from an .ibw (Igor binary wave) file and display all entries as a table of key/value pairs.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | FILE_PATH | No | File path from a Folder or other path node; overrides the filename widget |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| note | DATA_TABLE | Key/value table of all metadata entries from the IBW note |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| filename | FILE_PICKER | "" | Path to the .ibw file; hidden when path input is connected |

## Limitations

- Only .ibw files are supported; other formats raise an error.
- If the .ibw note section is empty or missing, an error is raised.
