# Grain Visualization

Visualize labeled grains as geometric shapes — inscribed discs, bounding boxes, centroid markers, or fitted ellipses. Produces a mask image with the chosen shapes and a labeled field where each grain has a unique integer value. Equivalent to Gwyddion's grain selection visualization (grain_makesel).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Source data field providing spatial reference and calibration |
| mask | IMAGE | Yes | Binary grain mask (white = grain region) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | IMAGE | Visualization mask with geometric shapes drawn for each grain |
| labeled | DATA_FIELD | Labeled field where each connected grain region has a unique integer value |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| style | dropdown | inscribed_disc | Visualization style: inscribed_disc, bounding_box, centroid, or ellipse |
| fill | BOOLEAN | False | When enabled, shapes are filled; when disabled, only outlines are drawn |

## Notes

- **inscribed_disc**: Draws a circle at each grain centroid with the inscribed disc radius (maximum of the distance transform within the grain).
- **bounding_box**: Draws an axis-aligned rectangle around each grain's bounding box.
- **centroid**: Draws small cross markers at each grain's centroid.
- **ellipse**: Fits an ellipse to each grain using the inertia tensor to determine the major/minor axes and orientation angle.
- When fill is disabled, outlines are drawn with approximately 1-2 pixel thickness.
- The labeled output assigns each connected grain region a unique positive integer; background pixels are zero.
- The mask and field must have the same pixel dimensions.
