# Grain Distance Transform

Compute the mask distance transform using Gwyddion-style interior, exterior, or signed output. Supports Euclidean, city-block, chessboard, and octagonal distance variants, with optional image-boundary handling matching mask_edt.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Field providing physical calibration for the output |
| mask | IMAGE | Yes | Binary mask to compute distances for |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| distance | DATA_FIELD | Distance transform field in physical units |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| distance_type | dropdown | euclidean | Distance metric: euclidean, cityblock, chess (Chebyshev), octagonal48, octagonal84, or octagonal |
| output_type | dropdown | interior | Output mode: interior (distances inside grains), exterior (distances outside), or signed (positive inside, negative outside) |
| from_border | BOOLEAN | True | When enabled, image borders are treated as mask boundaries |

## Notes

- Output distances are in physical xy units derived from the field calibration.
- The mask must have the same pixel dimensions as the field.
