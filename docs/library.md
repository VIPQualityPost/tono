# Using tono as a Python library

tono's processing nodes can be used as a standalone Python library for scripting, batch processing, and integration into other tools — no web server required.

## Installation

```bash
pip install -e .
```

This installs the core library with all signal processing dependencies (numpy, scipy, scikit-image, etc.) but **not** the web server (aiohttp). To install the full app with the server, use `pip install -e ".[server]"`.

## Quick start

```python
import tono

# Load an SPM data file
fields = tono.load("scan.gwy")
height = fields[0]

# Apply a processing node
leveled = tono.apply("PlaneLevelField", height)
filtered = tono.apply("GaussianFilter", leveled, sigma=2.0)

# Access the raw numpy array
print(filtered.data.shape)   # (256, 256)
print(filtered.data.mean())  # height in metres
```

## API reference

### Loading data

#### `tono.load(path) -> list[DataField]`

Load an SPM data file. Returns one `DataField` per channel.

```python
fields = tono.load("scan.gwy")       # Gwyddion
fields = tono.load("image.sxm")      # Nanonis
fields = tono.load("data.ibw")       # Igor Binary Wave
fields = tono.load("scan.hdf5")      # HDF5
fields = tono.load("photo.png")      # Standard images
```

#### `tono.channel_names(path) -> list[str]`

Get channel names without loading the full data.

```python
names = tono.channel_names("scan.gwy")
# ['Height', 'Phase', 'Amplitude']
```

#### `tono.supported_formats() -> frozenset[str]`

List all supported file extensions.

### Processing

#### `tono.apply(node_name, *args, **kwargs)`

Run a processing node. Positional arguments are mapped to required inputs in declaration order. Returns a single output if the node has one output, or a tuple if it has multiple.

```python
# Positional: first required input is `field`
result = tono.apply("GaussianFilter", my_field, sigma=3.0)

# All keyword arguments
result = tono.apply("GaussianFilter", field=my_field, sigma=3.0)

# Nodes with multiple outputs return a tuple
field_out, mask_out = tono.apply("ThresholdMask", my_field, method="otsu")
```

#### `tono.get_node(name) -> node_instance`

Get a node instance for direct use. This gives full control over the node's `process()` method.

```python
gauss = tono.get_node("GaussianFilter")
(result,) = gauss.process(field=my_field, sigma=3.0)
```

#### `tono.nodes() -> list[str]`

List all available node class names.

```python
for name in tono.nodes():
    print(name)
```

### Creating data

#### `tono.field(data, xreal=1e-6, yreal=1e-6, ...) -> DataField`

Create a `DataField` from a numpy array.

```python
import numpy as np

# From a numpy array
f = tono.field(np.random.randn(256, 256))

# With physical dimensions (10 um x 10 um scan)
f = tono.field(data, xreal=10e-6, yreal=10e-6, si_unit_z="V")
```

### Data types

#### `DataField`

The core 2D data container, analogous to Gwyddion's `GwyDataField`.

| Attribute | Type | Description |
|---|---|---|
| `data` | `np.ndarray` | 2D float64 array (yres x xres) |
| `xres`, `yres` | `int` | Pixel dimensions |
| `xreal`, `yreal` | `float` | Physical dimensions in metres |
| `dx`, `dy` | `float` | Pixel size in metres (property) |
| `si_unit_xy` | `str` | Lateral unit (e.g. `"m"`) |
| `si_unit_z` | `str` | Value unit (e.g. `"m"`, `"V"`, `"A"`) |
| `domain` | `str` | `"spatial"` or `"frequency"` |

Key methods:
- `field.copy()` — deep copy
- `field.replace(data=..., si_unit_z=...)` — copy with selected fields replaced

#### Other types

- `LineData` — 1D data with optional x-axis and units
- `RecordTable` — list of `{quantity, value, unit}` dicts (scalar measurements)
- `DataTable` — list of row dicts (tabular data like grain statistics)

## Batch processing example

```python
import tono
from pathlib import Path

input_dir = Path("scans/")
results = {}

for path in input_dir.glob("*.gwy"):
    fields = tono.load(path)
    height = fields[0]

    # Standard processing pipeline
    leveled = tono.apply("PlaneLevelField", height)
    filtered = tono.apply("GaussianFilter", leveled, sigma=1.5)

    # Extract statistics
    stats_node = tono.get_node("Statistics")
    (table,) = stats_node.process(field=filtered)
    results[path.name] = table

    print(f"{path.name}: processed {height.xres}x{height.yres} "
          f"({height.xreal*1e6:.1f} x {height.yreal*1e6:.1f} um)")
```

## Integration with matplotlib

```python
import tono
import matplotlib.pyplot as plt
import numpy as np

fields = tono.load("scan.gwy")
field = fields[0]

# Convert physical coordinates for axis labels
extent = [0, field.xreal * 1e6, 0, field.yreal * 1e6]  # in micrometres

fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].imshow(field.data * 1e9, extent=extent, cmap="afmhot")
axes[0].set_title("Raw")
axes[0].set_xlabel("x (um)")
axes[0].set_ylabel("y (um)")

leveled = tono.apply("PlaneLevelField", field)
axes[1].imshow(leveled.data * 1e9, extent=extent, cmap="afmhot")
axes[1].set_title("Leveled")

filtered = tono.apply("GaussianFilter", leveled, sigma=2.0)
axes[2].imshow(filtered.data * 1e9, extent=extent, cmap="afmhot")
axes[2].set_title("Filtered")

for ax in axes:
    ax.set_xlabel("x (um)")

plt.tight_layout()
plt.savefig("pipeline.png", dpi=150)
```

## Available nodes

Use `tono.nodes()` to list all nodes. Major categories include:

| Category | Example nodes |
|---|---|
| **Level & Correct** | PlaneLevelField, PolyLevelField, FacetLevelField, LineCorrection, DriftCorrection |
| **Filter** | GaussianFilter, MedianFilter, KuwaharaFilter, WaveletDenoise, EdgeDetect |
| **Spectral** | FFT2D, FFT2DInverse, FFTFilter, PSDF, ACF2D, CrossCorrelate |
| **Measure** | Statistics, Histogram, CrossSection, Curvature, FractalDimension |
| **Detect** | FeatureDetection, HoughTransform, TemplateMatch, PixelClassification |
| **Mask** | ThresholdMask, GrainMark, DrawMask, MaskMorphology |
| **Grains** | GrainAnalysis, WatershedSegmentation, GrainDistributions |
| **Geometry** | CropResizeField, RotateField, Resample, AffineCorrection |
| **Tip** | TipModel, TipDeconvolution, BlindTipEstimate |
