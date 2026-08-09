# Hough Transform

Detect lines or circles in images using the Hough transform. Returns an accumulator image and a table of detected features.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field (edge-detected images work best) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| accumulator | DATA_FIELD | Hough accumulator space |
| detections | RECORD_TABLE | Table of detected lines or circles |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | lines | Detection mode: lines or circles |
| n_peaks | INT | 3 | Number of strongest features to report (1-50) |
| threshold | FLOAT | 1.0 | Minimum accumulator value relative to peak (0.1-10.0) |
| min_radius | INT | 10 | Minimum circle radius in pixels (circles mode only) |
| max_radius | INT | 30 | Maximum circle radius in pixels (circles mode only) |

## Notes

- For line detection, apply Edge Detect first for best results. Lines are reported as (angle, distance) pairs.
- For circle detection, min/max radius constrains the search range. Circles are reported as (center_x, center_y, radius).
- The accumulator image visualises the parameter space — bright spots correspond to detected features.
