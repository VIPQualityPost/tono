# Testing

## Running tests

```bash
# Run all tests
python -m pytest -q

# Run with coverage report
python -m pytest -q --cov=backend --cov-report=term-missing

# Run a single test file
python -m pytest tests/node_tests/gaussian_filter.py -v

# Run a single test by name
python -m pytest tests/test_grains.py::test_threshold_otsu_bimodal -v
```

The test suite is configured in `pytest.ini` at the repo root. All tests under `tests/` are collected automatically, with the exception of private files (names starting with `_`).

---

## Test structure

```
tests/
  node_tests/          # One file per node or node group
    _shared.py         # Shared helpers (not collected as tests)
    gaussian_filter.py
    fft_2d.py
    ...
  test_grains.py       # Integration tests
  test_fft.py
  test_session_runtime.py
  test_frontend_build.py
```

**`tests/node_tests/`** contains per-node unit tests. Each file exercises a single node class or closely related group using the execution engine. Files are auto-collected by pytest; files whose names start with `_` are excluded.

**`tests/`** (top level) contains broader integration tests that cut across multiple nodes or test server-level behaviour.

---

## Writing tests

### Imports

```python
import numpy as np
import backend.nodes          # registers all built-in nodes as a side-effect
from backend.execution import ExecutionEngine
from tests.node_tests._shared import make_field
```

`import backend.nodes` must appear before any test that uses a built-in node, because node registration happens at import time via `@register_node`.

### The `make_field` helper

```python
from tests.node_tests._shared import make_field

# Default: 64×64 random field, xreal=yreal=1e-6 m, units "m"/"m"
field = make_field()

# Custom shape and physical size
field = make_field(shape=(128, 256), xreal=5e-6, yreal=5e-6)

# Custom data
field = make_field(data=np.zeros((32, 32)))
```

### Executing a node

Use the `ExecutionEngine` with the prompt format:

```python
def test_my_node():
    engine = ExecutionEngine()
    prompt = {
        "1": {
            "class_type": "GaussianFilter",
            "inputs": {
                "field": make_field(),   # pass objects directly in tests
                "sigma": 1.5,
            },
        }
    }
    outputs = engine.execute(prompt)
    result = outputs["1"][0]            # first output of node "1"
    assert result.data.shape == (64, 64)
```

Outputs are returned as a dict mapping node id → tuple of output values, in the same order as `OUTPUTS`.

### Linking nodes

To chain nodes, use a `[node_id, slot_index]` link in the inputs dict:

```python
prompt = {
    "1": {"class_type": "GaussianFilter", "inputs": {"field": make_field(), "sigma": 1.5}},
    "2": {"class_type": "PlaneLevelField", "inputs": {"field": ["1", 0]}},
}
outputs = engine.execute(prompt)
result = outputs["2"][0]
```

### Testing your own node class directly

You can also instantiate and call a node class directly without the engine:

```python
from backend.node_registry import register_node
from backend.data_types import DataField

def test_process_directly():
    field = make_field()
    node = MyNode()
    result, = node.process(field=field, sigma=2.0)
    assert isinstance(result, DataField)
```

### Assertions on DataField

```python
result = outputs["1"][0]

assert isinstance(result, DataField)
assert result.data.shape == (64, 64)
assert result.si_unit_z == "m"
assert np.isfinite(result.data).all()

# Physical dimensions are preserved by field.replace()
assert result.xreal == field.xreal
assert result.yreal == field.yreal
```

---

## Coverage

Coverage is configured in `pyproject.toml` under `[tool.coverage]`. It measures the `backend` package and excludes `backend/nodes/__init__.py`.

```bash
python -m pytest -q --cov=backend --cov-report=term-missing
```

The report shows which lines are not exercised by any test.
