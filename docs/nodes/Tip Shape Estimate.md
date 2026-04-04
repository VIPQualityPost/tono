# Tip Shape Estimate

Estimate SPM tip geometry from a known calibration feature. The image of a calibration feature (sharp edge, sphere, cylinder) is a dilation of the true feature shape with the tip. By subtracting the known feature contribution the tip shape can be recovered. The 2D tip is built by revolving the extracted 1D radial profile assuming axial symmetry. Equivalent to Gwyddion's tipshape.c analysis.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Image of a known calibration feature |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| tip_shape | DATA_FIELD | Estimated tip shape as a 2D image (apex = maximum, edges = 0) |
| parameters | RECORD_TABLE | Estimated tip parameters: tip_radius (radius of curvature at apex) and half_angle (cone half-angle from the tip walls) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| feature_type | dropdown | edge | Type of calibration feature: edge (sharp step), sphere (calibration ball), or cylinder (calibration wire) |
| feature_radius | FLOAT | 100 nm | Known radius of the calibration feature in metres; used for sphere and cylinder types (1 nm to 100 um) |
| n_points | INT | 100 | Number of points in the output tip profile / side length of the tip grid (10-1000) |

## Notes

- **Calibration features**: For best results use well-characterised calibration standards. Sharp edges give the most direct tip estimate. Sphere and cylinder features require accurate knowledge of the feature radius.
- **Dilation model**: The measured image is the morphological dilation of the true surface with the tip shape. For a known surface feature, subtracting the feature profile from the measured profile yields the tip contribution.
- **Axial symmetry assumption**: The 2D tip shape is built by revolving the 1D radial profile around the apex. This assumes the tip is rotationally symmetric, which is a reasonable first approximation for most SPM tips but may not capture asymmetric wear or contamination.
- **Use with Tip Deconvolution**: The estimated tip can be fed directly into the Tip Deconvolution node to reconstruct the true surface from measured images. Ensure the pixel size of the tip matches the image pixel size.
- **feature_radius** is only used for sphere and cylinder feature types; it is ignored for edge estimation.
- Equivalent to Gwyddion's tipshape.c tip characterisation routines.
