# Watershed Segmentation

Segment a height field into grains using the two-stage Gwyddion watershed workflow: drop-based seed location followed by watershed growth. Supports hill or valley detection and optional union/intersection with an existing mask.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input topographic field |
| mask | IMAGE | No | Optional existing mask to combine with the watershed result |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary grain mask from watershed segmentation |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| invert_height | BOOLEAN | False | When True, detects valleys instead of hills (inverts the height field) |
| locate_steps | INT | 10 | Number of drop steps in the seed location stage (1–200) |
| locate_threshold | INT | 10 | Minimum drop threshold for seed acceptance (0–100000) |
| locate_drop_size | FLOAT | 0.1 | Relative drop size for seed location stage (0.0001–1.0) |
| watershed_steps | INT | 20 | Number of steps in the watershed growth stage (1–2000) |
| watershed_drop_size | FLOAT | 0.1 | Relative drop size for watershed growth stage (0.0001–1.0) |
| combine_mode | dropdown | replace | How to combine with an existing mask: replace (ignore existing), union (OR), or intersection (AND) |

## Notes

- Parameter tuning is required; the default settings work best for isolated round features.
- Very large locate_threshold values may reject all seeds and produce an empty mask.
