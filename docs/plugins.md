# Writing plugins

Plugins are plain Python files dropped into the `plugins/` directory. Each file registers one or more nodes that appear in the Add Node menu immediately — no restart required if uploaded via UI upload.

A complete, annotated example is at [plugins/example_normalize.py](../plugins/example_normalize.py).

> **Note:** The plugin system is enabled on native desktop builds and disabled on web deployments by default. Override with the `TONO_PLUGINS=1` environment variable.

---

## Minimal plugin

```python
# plugins/my_filter.py
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField

@register_node(display_name="My Filter")
class MyFilter:
    CATEGORY = "Plugins"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            }
        }

    OUTPUTS = (("DATA_FIELD", "result"),)
    FUNCTION = "process"

    def process(self, field: DataField, strength: float) -> tuple:
        scaled = field.data * strength
        return (field.replace(data=scaled),)
```

Drop this file into `plugins/` and the node appears under **Plugins → My Filter** in the Add Node menu.

---

## Node class attributes

| Attribute | Required | Description |
|---|---|---|
| `INPUT_TYPES` | Yes | Classmethod returning `{"required": {...}, "optional": {...}}` |
| `OUTPUTS` | Yes | Tuple of `(type, name)` or `(type, name, meta)` entries |
| `FUNCTION` | Yes | Name of the method to call on execution |
| `CATEGORY` | No | Menu category; defaults to `"Unsorted"` if omitted |
| `DESCRIPTION` | No | Human-readable description shown in the UI |
| `OUTPUT_NODE` | No | Set `True` to mark this node as a terminal output node |
| `MANUAL_TRIGGER` | No | Set `True` to require the user to click Run manually |

---

## Input types

### Data types (socket connections)

These appear as connectable sockets on the node. They cannot be set inline by the user — they must be wired from another node.

| Type string | Python type received | Description |
|---|---|---|
| `"DATA_FIELD"` | `DataField` | 2D spatial/height data with physical metadata |
| `"IMAGE"` | `np.ndarray` (uint8) | Greyscale (H×W) or RGB (H×W×3) image or mask |
| `"LINE"` | `LineData` | 1D profile data with optional X axis and units |
| `"RECORD_TABLE"` | `RecordTable` (list of dicts) | Named scalar measurements |
| `"MESH_MODEL"` | `MeshModel` | 3D triangle mesh |

### Widget types (inline controls)

These appear as UI controls on the node body. They can also be connected from another node's output socket.

#### FLOAT

```python
"sigma": ("FLOAT", {
    "default": 1.0,
    "min": 0.0,      # optional
    "max": 10.0,     # optional
    "step": 0.1,     # optional, default step for dragging
})
```

Add `"socket_only": True` in the optional dict to suppress the widget and show only a socket:

```python
# optional section:
"value": ("FLOAT", {"socket_only": True}),
```

#### INT

```python
"count": ("INT", {
    "default": 5,
    "min": 1,
    "max": 100,
    "step": 1,
})
```

#### Dropdown / choice list

Pass a list as the first element of the spec tuple:

```python
"method": (["nearest", "bilinear", "bicubic"],),
# or with a default:
"method": (["nearest", "bilinear", "bicubic"], {"default": "bilinear"}),
```

#### STRING

```python
"label": ("STRING", {
    "default": "",
    "placeholder": "Enter text...",  # optional
    "multiline": False,              # optional
})
```

### Optional inputs

Declare inputs under `"optional"` to make them not required for execution. Your `process()` method receives `None` for any unconnected optional input, so guard against it:

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {"field": ("DATA_FIELD",)},
        "optional": {"mask": ("IMAGE",)},
    }

def process(self, field, mask=None):
    if mask is not None:
        # use mask
        ...
```

---

## Output types

Each entry in `OUTPUTS` is `(type_string, display_name)` or `(type_string, display_name, meta_dict)`.

| Type string | Python value to return | Description |
|---|---|---|
| `"DATA_FIELD"` | `DataField` | 2D spatial data |
| `"IMAGE"` | `np.ndarray` (uint8) | Greyscale or RGB image / mask |
| `"LINE"` | `LineData` | 1D profile |
| `"RECORD_TABLE"` | `RecordTable` | Named scalar measurement table |
| `"FLOAT"` | `float` | Scalar number |

The return value of `process()` must be a **tuple** with one item per `OUTPUTS` entry, in the same order:

```python
OUTPUTS = (
    ("DATA_FIELD", "result"),
    ("RECORD_TABLE", "stats"),
    ("FLOAT", "mean"),
)

def process(self, field):
    ...
    return (result_field, table, mean_value)   # must be a tuple
```

### Accepting multiple input types on one output slot

Use `accepted_types` in the output metadata to allow wiring from additional types:

```python
OUTPUTS = (
    ("DATA_FIELD", "output", {"accepted_types": ["IMAGE"]}),
)
```

---

## Data types reference

### DataField

The main SPM data container. Designed similar to Gwyddion's `GwyDataField`.

```python
@dataclass
class DataField:
    data: np.ndarray      # shape (yres, xres), dtype float64
    xres: int             # pixel count in X (set automatically from data)
    yres: int             # pixel count in Y (set automatically from data)
    xreal: float          # physical width in metres
    yreal: float          # physical height in metres
    xoff: float           # X position offset in metres
    yoff: float           # Y position offset in metres
    si_unit_xy: str       # lateral unit, e.g. "m"
    si_unit_z: str        # value unit, e.g. "m", "V", "A"
    domain: str           # "spatial" or "frequency"
    colormap: str | dict  # colormap name or custom dict
    display_offset: float # normalized display window offset
    display_scale: float  # normalized display window scale
    overlays: list        # list of overlay dicts (annotations etc.)

# Computed properties:
field.dx  # physical pixel size X = xreal / xres (metres)
field.dy  # physical pixel size Y = yreal / yres (metres)
```

**Always use `field.replace()` instead of constructing a new `DataField`** — it copies all metadata and only substitutes what you specify:

```python
# Good: physical dimensions, units, colormap all preserved
result = field.replace(data=new_data)

# Also valid: change data and units together
result = field.replace(data=fft_data, si_unit_z="1/m", domain="frequency")
```

Available built-in colormaps: `viridis`, `gray`, `hot`, `jet`, `plasma`, `inferno`, `terrain`, `cividis`, `magma`, `copper`, `afmhot`.

### LineData

1D profile data.

```python
@dataclass
class LineData:
    data: np.ndarray           # 1D float64 array of Y values
    x_axis: np.ndarray | None  # optional 1D float64 array of X positions
    x_unit: str                # unit label for X axis
    y_unit: str                # unit label for Y axis

# Supports NumPy interface transparently:
np.asarray(line)    # → line.data
len(line)           # → len(line.data)
line[i]             # → line.data[i]
```

### MeshModel

3D triangle mesh for the 3D view node.

```python
@dataclass
class MeshModel:
    vertices: np.ndarray       # shape (N, 3), float32 — XYZ positions
    faces: np.ndarray          # shape (M, 3), int32  — triangle vertex indices
    colors: np.ndarray | None  # shape (N, 3), uint8  — per-vertex RGB (optional)
```

### RecordTable

A measurement table: a plain list of `{"quantity", "value", "unit"}` dicts. Can be wired to the **Print Table** or **Save** nodes.

```python
from backend.data_types import RecordTable

table = RecordTable([
    {"quantity": "RMS roughness", "value": 2.34e-9, "unit": "m"},
    {"quantity": "Mean",          "value": 0.12e-9, "unit": "m"},
    {"quantity": "Pixel count",   "value": 4096,    "unit": ""},
])
```

Use `field.si_unit_z` for the physical Z unit of the input field. Use `""` for dimensionless quantities.

---

## Execution context: emit functions

Import from `backend.execution_context` to send data to the frontend during execution — for example, to show a preview chart or a warning message.

```python
from backend.execution_context import emit_preview, emit_table, emit_warning, emit_value
```

| Function | Description |
|---|---|
| `emit_preview(data_uri)` | Push a preview image (base64 data URI string) to the preview panel |
| `emit_table(rows)` | Push a list of dicts as a table update |
| `emit_value(payload)` | Push a scalar value (or `{"value": v, "unit": "m"}` dict) |
| `emit_warning(message)` | Show a warning banner in the UI |

These functions are no-ops if called outside an active execution context, so they are safe to call unconditionally.

```python
from backend.execution_context import emit_warning

def process(self, field, threshold):
    if threshold > field.data.max():
        emit_warning("Threshold is above the data maximum — result will be empty.")
    ...
```

---

## Multi-file plugins

A directory with an `__init__.py` is treated as a plugin package. Private helpers (names starting with `_`) are ignored by the loader.

```
plugins/
  my_suite/
    __init__.py          # registers nodes with @register_node
    _helpers.py          # private helpers, not auto-loaded
```

In `__init__.py`:

```python
from backend.node_registry import register_node
from backend.data_types import DataField
from my_suite._helpers import compute_something

@register_node(display_name="Suite Node A")
class SuiteNodeA:
    ...
```

---

## Uploading plugins via the web interface

On native builds, plugins can be uploaded without restarting via the toolbar.

The server saves the file, hot-reloads all plugins, and broadcasts a `nodes_updated` WebSocket message so the frontend refreshes the node list automatically.

> **Security note:** Uploading a `.py` file is equivalent to executing arbitrary code inside the server process. Only expose this endpoint on trusted local networks.
