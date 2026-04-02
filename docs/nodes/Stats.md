# Stats

Compute a contextual scalar statistic from a LINE, record table, DATA_FIELD, or IMAGE. The available operations adapt to the connected input type.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input | DATA_FIELD, IMAGE, LINE, or DATA_TABLE | Yes | Input to compute statistics on |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| value | FLOAT | Computed scalar statistic |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | STRING (context-dependent dropdown) | mean | Statistical operation; available choices depend on the input type |
| column | STRING | value | Column name for DATA_TABLE inputs; visible only when a DATA_TABLE is connected |

## Notes

- Available operations vary by input type; connecting a different type changes the available options.
- For DATA_TABLE inputs, the column must match an existing column name; an error is raised otherwise.
