# Font

Build a reusable font specification for annotation overlays. Choose a discovered system font, use the default fallback stack, or point to a custom font file.

## Inputs

None.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| font | FONT | Font specification for use with Annotations and similar nodes |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| family | dropdown | System default | Font family name; includes discovered system fonts plus "Custom file" option |
| font_file | FILE_PICKER | "" | Path to a custom font file; visible only when family is set to "Custom file" |

## Limitations

- Custom font files must be in a format supported by the underlying font rendering library (e.g. TTF, OTF).
- System fonts are enumerated at startup; newly installed fonts require restarting the application.
