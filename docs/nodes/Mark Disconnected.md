# Mark Disconnected

Mark topologically disconnected (isolated) surface regions. A morphological opening followed by closing builds a smooth defect-free reference surface; pixels whose deviation from that reference exceeds the sensitivity threshold are flagged. Equivalent to Gwyddion's mark_disconn.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface to analyse for disconnected regions |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask (0/255) marking detected disconnected regions |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| defect_type | dropdown | positive | Which direction of outliers to detect: positive (bumps), negative (pits), or both |
| radius | INT | 5 | Morphological filter radius in pixels (1--100). Larger values smooth over bigger features |
| threshold | FLOAT | 0.1 | Sensitivity threshold as a fraction of the max residual range (0.001--1.0). Lower values detect smaller defects |

## Notes

- The algorithm applies grey-scale morphological opening then closing with a disk structuring element to produce a defect-free reference. The difference between the original surface and this reference highlights isolated regions.
- Increase the radius to ignore larger surface features and only flag truly disconnected regions.
- Lower the threshold to catch subtler defects; raise it to reduce false positives.
- The resulting mask can be fed to Laplace Interpolation or Fractal Interpolation to fill the detected regions.
