# Using tono as a Python library

tono's processing nodes can be used as a standalone Python library for scripting, batch processing, and integration into other tools — no web server required. It works best as part of a notebook style workflow (Jupyter, IPython).

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

# Every registered node is available as a top-level callable
leveled, plane = tono.PlaneLevelField(height)
filtered = tono.GaussianFilter(leveled, sigma=2.0)

# Access the raw numpy array
print(filtered.data.shape)   # (256, 256)
print(filtered.data.mean())  # height in metres
```

## Discovering node signatures

Every node carries a real `inspect.Signature` synthesised from its input
declarations, so `help()`, Jupyter's `?`, and IPython tab-completion all show
the correct parameters, types, defaults, and enum choices:

```python
>>> help(tono.EdgeDetect)
EdgeDetect(
    field: DataField,
    method: Literal['sobel', 'prewitt', 'laplacian', 'log'],
    sigma: float = 1.0,
) -> DataField
    Detect edges using Sobel, Prewitt, Laplacian, or LoG operators.
    ...
```

`dir(tono)` lists every registered node — useful for tab-completion and
programmatic discovery.

## API reference

### Loading data

#### `tono.load(path) -> list[DataField]`

Load an SPM data file. Returns one `DataField` per channel.

```python
fields = tono.load("scan.hdf5")  
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

There are two equivalent ways to invoke a node. Both return a single value
when the node has one output, or a tuple when it has multiple.

#### `tono.NodeName(*args, **kwargs)` — typed call syntax

Recommended for scripts and notebooks. Each node is exposed as a top-level
callable with a real `inspect.Signature`, so your editor, `help()`, and Jupyter
all know the parameters and defaults:

```python
# Positional arguments map to required inputs in declaration order
result = tono.GaussianFilter(my_field, sigma=3.0)

# Fully keyword — order-independent
result = tono.GaussianFilter(field=my_field, sigma=3.0)

# Defaults declared in the node's INPUT_TYPES metadata are auto-filled
result = tono.GaussianFilter(my_field)  # uses sigma=1.0 from metadata

# Multi-output nodes return a tuple
log_mag, mag, phase, psdf = tono.FFT2D(my_field, windowing="hann", level="mean")
```

#### `tono.apply(node_name, *args, **kwargs)` — string-based dispatch

Use this when the node name is only known at runtime (e.g. a user-selected
pipeline). Same arg conventions, same default-filling behaviour.

```python
name = choose_node_from_config()
result = tono.apply(name, my_field, sigma=3.0)
```

#### `tono.describe(name) -> dict`

Return a dict describing a node's inputs, outputs, description, keywords, and
category. Thin wrapper around the registry metadata used by the web UI.

```python
info = tono.describe("EdgeDetect")
print(info["input"]["required"].keys())  # dict_keys(['field', 'method', 'sigma'])
print(info["output_name"])               # ['edges']
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

The core 2D data container, analogous to `GwyDataField`.

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
    leveled, plane = tono.PlaneLevelField(height)
    filtered = tono.GaussianFilter(leveled, sigma=1.5)

    # Scalar measurements
    table = tono.Statistics(filtered)
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

leveled, plane = tono.PlaneLevelField(field)
axes[1].imshow(leveled.data * 1e9, extent=extent, cmap="afmhot")
axes[1].set_title("Leveled")

filtered = tono.GaussianFilter(leveled, sigma=2.0)
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
| **SPM** | MFMAnalysis, MFMDomainGeneration, MFMParallelMedia, SMMAnalysis, SEMSimulation |
| **Probe** | TipModel, TipDeconvolution, BlindTipEstimate, TipShapeEstimate, PSFEstimation |
