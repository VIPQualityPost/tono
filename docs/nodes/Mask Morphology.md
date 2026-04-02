# Mask Morphology

Apply morphological operations to a binary mask. Dilate expands regions, erode shrinks them, open (erode then dilate) removes small islands, and close (dilate then erode) fills small holes. Equivalent to Gwyddion's mask_morph.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mask | IMAGE | Yes | Binary mask to process |
| field | DATA_FIELD | No | Optional field for preview background display |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Morphologically processed binary mask |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | dilate | Morphological operation: dilate, erode, open, or close |
| radius | INT | 1 | Structuring element radius in pixels (1–50) |
| shape | dropdown | disk | Structuring element shape: disk or square |

## Notes

- Large radius values (> ~20 pixels) may be slow on large masks.
