# Tip Model

Generate a synthetic AFM tip model DATA_FIELD. The input field sets the pixel size for the tip. The apex (center pixel) is the maximum value; edges are shifted to zero. Equivalent to gwy_tip_model_preset_create (tip.c / tip_model.c).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Reference field that sets the tip pixel size |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| tip | DATA_FIELD | Synthetic tip shape field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| shape | dropdown | parabola | Tip geometry: parabola (paraboloid with apex radius R), cone (sphere-capped cone), or sphere (ball-on-stick) |
| radius | FLOAT | 10 nm | Apex radius of curvature in metres (1e-10 to 1e-6) |
| half_angle | FLOAT | 20.0 | Half-cone angle from the tip axis in degrees for the cone shape (1-89°) |
| n_pixels | INT | 65 | Side length of the square tip grid in pixels (odd values only, 3-511) |

## Notes

- half_angle is only used for the cone shape.
- The tip grid must be smaller than or equal to the image size for Tip Deconvolution to work correctly.
- Large n_pixels values produce large tip grids that make deconvolution slow.
