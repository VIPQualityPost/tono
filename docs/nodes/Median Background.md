# Median Background

Extract background using a local median filter and subtract it. The radius controls the filter window — larger values capture broader background variations. More robust than polynomial leveling for surfaces with sparse tall features.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Background-subtracted field or extracted background |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| radius | INT | 20 | Half-size of the median filter window in pixels; the full window is (2×radius+1)² (2-500) |
| output | dropdown | subtracted | Output mode: subtracted (original minus background) or background (extracted background) |

## Notes

- The median filter is robust to outliers — tall features (particles, grains) do not bias the background estimate.
- Choose a radius larger than your largest feature but smaller than the background curvature scale.
- For polynomial background removal, use Plane Level or Polynomial Level instead.
- Processing time increases with radius; for very large fields, consider downsampling first.
