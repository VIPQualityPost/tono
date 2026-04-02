# 3D View

Interactive 3D surface view of a DATA_FIELD. Use the mesh input for geometry and optionally a second map input for coloring. Drag to rotate, middle-drag to pan, and right-drag or scroll to zoom.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Height field used for mesh geometry |
| map_field | DATA_FIELD | No | Optional separate field used for surface coloring |
| colormap_map | COLORMAP | No | Colormap socket; overrides the colormap widget |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mesh | MESH_MODEL | Triangulated 3D surface mesh |
| viewport | IMAGE | Snapshot of the 3D viewport |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| colormap | dropdown | auto | Colormap preset applied to the surface; hidden when colormap_map is connected |
| z_scale | FLOAT | 1.0 | Height exaggeration factor (range 0.1–10.0) |
| resolution | INT | 128 | Downsampling resolution for mesh generation (32–512) |
| make_solid | BOOLEAN | False | When enabled adds a flat base and side walls to close the mesh |

## Notes

- Resolution is applied by uniform subsampling; fine features smaller than one mesh step may be lost.
- Non-square pixels emit a warning and the 3D surface represents physical scan area, not pixel grid.
- Very high resolution values (close to 512) with large fields may be slow to render.
