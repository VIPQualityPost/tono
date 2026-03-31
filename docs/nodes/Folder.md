# Folder

Pick a folder and output its directory path plus one file socket per compatible file inside it. Supported files include common images, .npy/.npz arrays, and .gwy/.sxm/.ibw scans.

## Inputs

None.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| directory | DIRECTORY | The selected folder path |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| folder | FOLDER_PICKER | "" | Path to the folder to list |

## Limitations

- Only files with supported extensions are listed; subdirectories and unsupported file types are ignored.
- The number of file output sockets is determined at load time by the folder contents.
