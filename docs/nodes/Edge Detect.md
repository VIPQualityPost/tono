# Edge Detect

Detect edges using Sobel, Prewitt, Laplacian, or Laplacian-of-Gaussian (LoG) operators. Equivalent to gwy_data_field_filter_sobel / gwy_data_field_filter_laplacian.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| edges | DATA_FIELD | Edge-detected output field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | sobel | Edge detection operator: sobel, prewitt, laplacian, or log (Laplacian of Gaussian) |
| sigma | FLOAT | 1.0 | Gaussian smoothing sigma used only for the LoG operator (0.1–10.0) |

## Limitations

- sigma is ignored for sobel, prewitt, and laplacian methods.
- Sobel and Prewitt return gradient magnitude; Laplacian and LoG return signed second-derivative values.
