# Facet Level

Level a field by iteratively finding the dominant local facet orientation and subtracting the corresponding plane. Matches Gwyddion's facet-level behaviour. Supports mask include/exclude selection.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input topographic field |
| mask | IMAGE | No | Binary mask for including or excluding facets from plane fitting |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with dominant facet plane subtracted |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| masking | dropdown | exclude | How to use the mask: exclude (ignore masked facets), include (use only masked facets), or ignore (use all facets) |

## Limitations

- Requires compatible XY and Z physical units for correct facet gradient estimation.
- Needs at least four valid facet cells; fields smaller than 2×2 pixels are not processed.
- Flat surfaces with no variation in facet orientation may not converge to a meaningful plane.
