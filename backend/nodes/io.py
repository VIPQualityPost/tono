"""
I/O nodes: load and save images and SPM data.
"""

from __future__ import annotations
import os
import re
import numpy as np
from pathlib import Path

from backend.node_registry import register_node
from backend.data_types import COLORMAPS, DataField, encode_preview, image_to_uint8, resolve_colormap_input
from backend.runtime_paths import demo_dir, input_dir, output_dir

# Resolved at server startup so nodes know where to look
DEMO_DIR = demo_dir()
INPUT_DIR = input_dir()
OUTPUT_DIR = output_dir()

_DEMO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".npy", ".npz",
                    ".gwy", ".sxm", ".ibw"}

_SPM_EXTENSIONS = {".gwy", ".sxm", ".ibw"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
_ARRAY_EXTENSIONS = {".npy", ".npz"}
_PATH_COMPATIBLE_EXTENSIONS = _IMAGE_EXTENSIONS | _ARRAY_EXTENSIONS | _SPM_EXTENSIONS


# ---------------------------------------------------------------------------
# Channel listing helper (used by the /channels endpoint)
# ---------------------------------------------------------------------------

def _resolve_path(filepath: str) -> Path:
    path = Path(filepath)
    if path.is_absolute():
        return path
    # Try input dir first, then demo dir
    candidate = INPUT_DIR / filepath
    if candidate.exists():
        return candidate
    candidate = DEMO_DIR / filepath
    if candidate.exists():
        return candidate
    # Fall back to input dir (will trigger FileNotFoundError later)
    return INPUT_DIR / filepath


def list_channels(filepath: str) -> list[dict]:
    """Return available channel info for a file.

    Returns a list of {"name": str, "type": "DATA_FIELD"} dicts.
    For SPM formats this inspects the file header.
    For images / arrays, returns a single unnamed channel.
    """
    path = _resolve_path(filepath)
    if not path.exists():
        return [{"name": "field", "type": "DATA_FIELD"}]

    ext = path.suffix.lower()

    if ext == ".gwy":
        try:
            import gwyfile
            obj = gwyfile.load(str(path))
            channels = gwyfile.util.get_datafields(obj)
            if channels:
                return [{"name": k, "type": "DATA_FIELD"} for k in channels]
        except Exception:
            pass
        return [{"name": "field", "type": "DATA_FIELD"}]

    if ext == ".sxm":
        try:
            import nanonispy as nap
            sxm = nap.read.Scan(str(path))
            if sxm.signals:
                return [{"name": k, "type": "DATA_FIELD"} for k in sxm.signals]
        except Exception:
            pass
        return [{"name": "field", "type": "DATA_FIELD"}]

    if ext == ".ibw":
        try:
            from igor.binarywave import load as load_ibw
            wave = load_ibw(str(path))
            raw = wave["wave"]["wData"]
            labels = wave["wave"].get("labels", None)
            if raw.ndim >= 3 and labels:
                dim_idx = min(2, len(labels) - 1)
                if dim_idx >= 0 and labels[dim_idx]:
                    decoded = []
                    for lbl in labels[dim_idx]:
                        if lbl:
                            name = lbl.split(b"\x00")[0].decode("ascii", errors="replace").strip()
                            if name:
                                decoded.append(name)
                    if decoded:
                        return [{"name": n, "type": "DATA_FIELD"} for n in decoded]
            # Multi-channel without labels — use numeric names
            if raw.ndim >= 3 and raw.shape[2] > 1:
                return [{"name": f"ch{i}", "type": "DATA_FIELD"} for i in range(raw.shape[2])]
        except Exception:
            pass
        return [{"name": "field", "type": "DATA_FIELD"}]

    # Image or array — single channel
    return [{"name": "field", "type": "DATA_FIELD"}]


def list_folder_paths(folderpath: str) -> list[dict]:
    """Return a folder DIRECTORY plus compatible image/array/SPM FILE_PATH outputs."""
    path = _resolve_path(folderpath)
    if not path.exists() or not path.is_dir():
        return []

    resolved_dir = str(path.resolve())
    results = [{"name": "directory", "type": "DIRECTORY", "path": resolved_dir}]
    for entry in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_file() or entry.name.startswith("."):
            continue
        if entry.suffix.lower() not in _PATH_COMPATIBLE_EXTENSIONS:
            continue
        results.append({"name": entry.name, "type": "FILE_PATH", "path": str(entry.resolve())})
    return results


# ---------------------------------------------------------------------------
# Image  (unified loader — replaces LoadImage + LoadSPM)
# ---------------------------------------------------------------------------

@register_node(display_name="Image")
class Image:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": "", "hide_when_input_connected": "path"}),
                "colormap": (list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
                "path": ("FILE_PATH", {"label": "path"}),
            },
        }

    # Default outputs — overridden dynamically by the frontend for multi-channel files
    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "load"

    DESCRIPTION = (
        "Load any supported file. "
        "SPM formats (.gwy, .sxm, .ibw) provide calibrated dimensions; "
        "each channel gets its own output. "
        "Images (.png, .tiff, .jpg) and arrays (.npy, .npz) are loaded as uncalibrated fields."
    )

    # Set by execution engine for warning broadcast
    _broadcast_warning_fn = None
    _current_node_id = None

    def load(self, filename: str = "", colormap: str = "viridis", colormap_map=None, path: str | None = None):
        selected_path = str(path).strip() if path is not None else str(filename).strip()
        if not selected_path:
            raise ValueError("No file selected — use Browse to pick a file.")
        path_obj = _resolve_path(selected_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")
        if path_obj.is_dir():
            raise IsADirectoryError(f"Expected a file, got a directory: {path_obj}")

        ext = path_obj.suffix.lower()
        resolved_colormap = resolve_colormap_input(colormap, colormap_input=colormap_map, default="viridis")

        if ext in _SPM_EXTENSIONS:
            fields = self._load_spm_all(path_obj, ext)
            for f in fields:
                f.colormap = resolved_colormap
            return tuple(fields)

        # Image or array — uncalibrated, single output
        field = self._load_image_or_array(path_obj, ext)
        field.colormap = resolved_colormap
        self._send_warning("Uncalibrated data — no physical dimensions.")
        return (field,)

    def _send_warning(self, message: str):
        fn = Image._broadcast_warning_fn
        nid = Image._current_node_id
        if fn and nid:
            fn(nid, message)

    # -- SPM: load all channels ---------------------------------------------

    def _load_spm_all(self, path: Path, ext: str) -> list[DataField]:
        if ext == ".gwy":
            return self._load_gwy_all(path)
        elif ext == ".sxm":
            return self._load_sxm_all(path)
        elif ext == ".ibw":
            return self._load_ibw_all(path)
        else:
            raise ValueError(f"Unsupported SPM format: {ext}")

    # -- GWY ----------------------------------------------------------------

    def _load_gwy_all(self, path: Path) -> list[DataField]:
        try:
            import gwyfile
        except ImportError:
            raise ImportError("Install 'gwyfile' package to load .gwy files: pip install gwyfile")

        obj = gwyfile.load(str(path))
        channels = gwyfile.util.get_datafields(obj)
        if not channels:
            raise ValueError(f"No data channels found in {path.name}")

        fields = []
        for ch in channels.values():
            data = np.array(ch.data, dtype=np.float64).reshape(ch.yres, ch.xres)
            fields.append(DataField(
                data=data,
                xreal=float(ch.xreal),
                yreal=float(ch.yreal),
                xoff=float(getattr(ch, "xoff", 0.0)),
                yoff=float(getattr(ch, "yoff", 0.0)),
                si_unit_xy="m",
                si_unit_z="m",
            ))
        return fields

    # -- SXM ----------------------------------------------------------------

    def _load_sxm_all(self, path: Path) -> list[DataField]:
        try:
            import nanonispy as nap
        except ImportError:
            raise ImportError("Install 'nanonispy' package to load .sxm files: pip install nanonispy")

        sxm = nap.read.Scan(str(path))
        signals = sxm.signals
        if not signals:
            raise ValueError(f"No signals found in {path.name}")

        header = sxm.header
        scan_range = header.get("scan_range", [1e-6, 1e-6])

        fields = []
        for sig in signals.values():
            data = sig.get("forward", list(sig.values())[0])
            data = np.asarray(data, dtype=np.float64)
            if data.ndim != 2:
                data = data.reshape(data.shape[-2], data.shape[-1])
            fields.append(DataField(
                data=data,
                xreal=float(scan_range[0]),
                yreal=float(scan_range[1]),
                si_unit_xy="m",
                si_unit_z="m",
            ))
        return fields

    # -- IBW ----------------------------------------------------------------

    def _load_ibw_all(self, path: Path) -> list[DataField]:
        try:
            from igor.binarywave import load as load_ibw
        except ImportError:
            raise ImportError("Install 'igor' package to load .ibw files: pip install igor")

        wave = load_ibw(str(path))
        wdata = wave["wave"]
        header = wdata["wave_header"]
        raw = wdata["wData"]

        n_channels = raw.shape[2] if raw.ndim >= 3 else 1

        # Physical scaling
        sfA = header.get("sfA", None)

        def _decode_unit(raw_unit):
            if raw_unit is None:
                return "m"
            if isinstance(raw_unit, bytes):
                return raw_unit.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or "m"
            if isinstance(raw_unit, np.ndarray):
                return bytes(raw_unit).split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or "m"
            return str(raw_unit).strip() or "m"

        dim_units_raw = header.get("dimUnits", None)
        data_units_raw = header.get("dataUnits", None)

        if isinstance(dim_units_raw, np.ndarray) and dim_units_raw.ndim == 2:
            si_unit_xy = _decode_unit(dim_units_raw[0])
        elif isinstance(dim_units_raw, (list, np.ndarray)) and len(dim_units_raw) > 0:
            si_unit_xy = _decode_unit(dim_units_raw[0])
        else:
            si_unit_xy = _decode_unit(dim_units_raw)

        si_unit_z = _decode_unit(data_units_raw)

        fields = []
        for ch_idx in range(n_channels):
            if raw.ndim >= 3:
                ch_data = raw[:, :, ch_idx]
            elif raw.ndim == 1:
                ch_data = raw.reshape(-1, 1)
            else:
                ch_data = raw

            # Transpose from (xres, yres) Igor order to (yres, xres) DataField order,
            # then flip vertically to match gwyddion
            data = np.flipud(ch_data.T).astype(np.float64)
            yres, xres = data.shape

            if sfA is not None and len(sfA) >= 2:
                xreal = abs(float(sfA[0]) * xres) or 1e-6
                yreal = abs(float(sfA[1]) * yres) or 1e-6
            else:
                hsA = header.get("hsA", 0.0)
                xreal = abs(float(hsA) * xres) or 1e-6
                yreal = xreal * (yres / xres) if xres else 1e-6

            fields.append(DataField(
                data=data, xreal=xreal, yreal=yreal,
                si_unit_xy=si_unit_xy, si_unit_z=si_unit_z,
            ))

        return fields

    # -- Image / array (uncalibrated) --------------------------------------

    def _load_image_or_array(self, path: Path, ext: str) -> DataField:
        if ext == ".npy":
            arr = np.load(str(path)).astype(np.float64)
        elif ext == ".npz":
            npz = np.load(str(path))
            key = list(npz.files)[0]
            arr = npz[key].astype(np.float64)
        else:
            from PIL import Image
            img = Image.open(str(path))
            arr = np.array(img)
            if arr.dtype != np.uint8:
                arr = arr.astype(np.float64)

        if arr.ndim == 3:
            gray = np.mean(arr.astype(np.float64), axis=2)
        else:
            gray = arr.astype(np.float64)

        return DataField(data=gray)


# ---------------------------------------------------------------------------
# ImageDemo
# ---------------------------------------------------------------------------

def _list_demo_files() -> list[str]:
    """Return sorted list of demo filenames available in the demo/ directory."""
    if not DEMO_DIR.exists():
        return []
    return sorted(
        f.name for f in DEMO_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in _DEMO_EXTENSIONS
    )


@register_node(display_name="Image (Demo)")
class ImageDemo:
    @classmethod
    def INPUT_TYPES(cls):
        choices = _list_demo_files() or ["(no demo files found)"]
        return {
            "required": {
                "name": (choices,),
                "colormap": (list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
            },
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "load"

    DESCRIPTION = "Load a bundled demo file so you can try the app without providing your own data."

    def load(self, name: str = "", colormap: str = "viridis", colormap_map=None):
        loader = Image()
        demo_path = DEMO_DIR / name
        if not demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {name}")
        return loader.load(filename=str(demo_path), colormap=colormap, colormap_map=colormap_map)


@register_node(display_name="Folder")
class Folder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder": ("FOLDER_PICKER", {"default": "", "placement": "top"}),
            }
        }

    RETURN_TYPES = ("DIRECTORY",)
    RETURN_NAMES = ("directory",)
    FUNCTION = "list_files"

    DESCRIPTION = (
        "Pick a folder and output its directory path plus one file socket per compatible image, array, or SPM file inside it. "
        "Supported files include common images, .npy/.npz arrays, and .gwy/.sxm/.ibw scans."
    )

    def list_files(self, folder: str) -> tuple:
        entries = list_folder_paths(folder)
        if not entries:
            return tuple()
        return tuple(item["path"] for item in entries)


# ---------------------------------------------------------------------------
# Coordinate
# ---------------------------------------------------------------------------

@register_node(display_name="Coordinate")
class Coordinate:
    """Provide a fractional (x, y) point for use with Cross Section or other nodes."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("COORD",)
    RETURN_NAMES = ("point",)
    FUNCTION = "process"

    DESCRIPTION = "Output a fractional (x, y) coordinate pair in [0, 1]."

    def process(self, x: float, y: float) -> tuple:
        return ((float(x), float(y)),)
    
    
@register_node(display_name="Coordinate Pair")
class CoordinatePair:
    """Provide a pair of Coordinates, for drawing lines between markers, etc."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("COORD",),
                "b": ("COORD",),
            }
        }
    
    RETURN_TYPES = ("COORDPAIR",)
    RETURN_NAMES = ("coord pair",)
    FUNCTION = "process"

    DESCRIPTION = "Output a pair of coordinates."

    def process(self, a: tuple, b: tuple) -> tuple:
        return ((a, b),)
    

# ---------------------------------------------------------------------------
# Number
# ---------------------------------------------------------------------------

@register_node(display_name="Number")
class Number:
    """Provide a fixed scalar value that can feed FLOAT or INT widget sockets."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("FLOAT", {"default": 0.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Output a fixed numeric value. "
        "When connected to FLOAT inputs the exact value is used; "
        "INT inputs round to the nearest integer at execution time."
    )

    def process(self, value: float) -> tuple:
        return (float(value),)


# ---------------------------------------------------------------------------
# RangeSlider
# ---------------------------------------------------------------------------

@register_node(display_name="Float Slider")
class RangeSlider:
    """Interactive float control node with min/max bounds and a slider value."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "max_value": ("FLOAT", {"default": 1.0, "step": 0.01}),
                "value": ("FLOAT", {
                    "default": 0.5,
                    "step": 0.01,
                    "slider": True,
                    "min_widget": "min_value",
                    "max_widget": "max_value",
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Interactive float slider. Set min and max bounds, then drag the slider to output a FLOAT value."
    )

    def process(self, min_value: float, max_value: float, value: float) -> tuple:
        lo = min(float(min_value), float(max_value))
        hi = max(float(min_value), float(max_value))
        if hi == lo:
            return (lo,)
        return (float(np.clip(float(value), lo, hi)),)


# ---------------------------------------------------------------------------
# SaveImage
# ---------------------------------------------------------------------------

_MAX_SAVE_FIELDS = 8

@register_node(display_name="Save Layers")
class SaveImage:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "directory": ("DIRECTORY", {"label": "directory"}),
        }
        for i in range(_MAX_SAVE_FIELDS):
            optional[f"field_{i}"] = ("SAVE_LAYER", {"label": f"layer {i + 1}"})
            optional[f"layer_name_{i}"] = ("STRING", {
                "default": "",
                "placeholder": "name",
                "show_when_input_visible": f"field_{i}",
                "inline_with_input": f"field_{i}",
                "hide_label": True,
            })
        return {
            "required": {
                "filename": ("STRING", {
                    "default": "",
                    "placeholder": "filename",
                    "placement": "top",
                }),
                "directory_path": ("FOLDER_PICKER", {
                    "default": "",
                    "label": "directory",
                    "placement": "top",
                    "hide_when_input_connected": "directory",
                    "top_socket_input": "directory",
                    }),
                "format": (["TIFF", "NPZ"],),
            },
            "optional": optional,
        }

    RETURN_TYPES = ()
    FUNCTION = "save"

    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save one or more layers to a single file. "
        "Each layer input accepts either a DATA_FIELD or an IMAGE, including annotated images. "
        "Optionally drive the output directory from a folder/path node, while keeping the filename widget for the file name. "
        "A new slot appears as each one is filled, with a matching per-layer name field. "
        "TIFF writes multi-page data and stores layer names as page descriptions; "
        "NPZ writes named arrays using those layer names as keys. "
        "Click Save to write (does not auto-run)."
    )

    _broadcast_warning_fn = None
    _current_node_id = None

    def save(
        self,
        filename: str,
        directory_path: str = "",
        format: str = "TIFF",
        directory: str | None = None,
        **kwargs,
    ):
        layers = []
        layer_names = []
        for i in range(_MAX_SAVE_FIELDS):
            layer = kwargs.get(f"field_{i}")
            if layer is not None:
                layers.append(layer)
                layer_names.append(self._resolve_layer_name(kwargs.get(f"layer_name_{i}"), i))

        if not layers:
            raise ValueError("No layers connected — connect at least one DATA_FIELD or IMAGE input.")

        path = self._resolve_save_path(filename, format, directory, directory_path)

        if format == "TIFF":
            self._save_tiff(path, layers, layer_names)
        else:
            self._save_npz(path, layers, layer_names)

        self._send_warning(f"Saved {len(layers)} layer(s) to {path.name}")
        return ()

    def _save_tiff(self, path: Path, layers: list[DataField | np.ndarray], layer_names: list[str]):
        import tifffile

        with tifffile.TiffWriter(str(path)) as tif:
            for layer, layer_name in zip(layers, layer_names):
                tif.write(self._layer_array_for_tiff(layer), description=layer_name)

    def _save_npz(self, path: Path, layers: list[DataField | np.ndarray], layer_names: list[str]):
        arrays = {}
        used_keys = set()
        for i, (layer, layer_name) in enumerate(zip(layers, layer_names)):
            arrays[self._unique_npz_key(layer_name, used_keys, i)] = self._layer_array_for_npz(layer)
        np.savez(str(path), **arrays)

    def _resolve_layer_name(self, raw_name: object, index: int) -> str:
        text = str(raw_name).strip() if raw_name is not None else ""
        return text or f"layer_{index}"

    def _resolve_save_path(
        self,
        filename: str,
        format: str,
        directory: str | None,
        directory_path: str = "",
    ) -> Path:
        ext = ".tiff" if format == "TIFF" else ".npz"
        raw_filename = str(filename).strip() if filename is not None else ""
        raw_directory = str(directory).strip() if directory is not None else ""
        if not raw_directory:
            raw_directory = str(directory_path).strip() if directory_path is not None else ""

        if raw_directory:
            dir_path = Path(raw_directory).expanduser()
            if dir_path.exists() and not dir_path.is_dir():
                raise ValueError("Directory input expects a folder path, not a file path.")
            if not dir_path.exists():
                if dir_path.suffix:
                    raise ValueError("Directory input expects a folder path, not a file path.")
                dir_path.mkdir(parents=True, exist_ok=True)

            filename_part = Path(raw_filename).name if raw_filename else ""
            if not filename_part:
                raise ValueError("No output filename selected — enter a file name when using a directory input.")
            path = dir_path / filename_part
        else:
            if not raw_filename:
                raise ValueError("No output path selected — use Browse to pick a location.")
            path = Path(raw_filename).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        return path

    def _unique_npz_key(self, raw_name: str, used_keys: set[str], index: int) -> str:
        key = re.sub(r"[^0-9A-Za-z_]+", "_", str(raw_name).strip()).strip("_")
        if not key:
            key = f"layer_{index}"
        if key[0].isdigit():
            key = f"layer_{key}"

        candidate = key
        suffix = 2
        while candidate in used_keys:
            candidate = f"{key}_{suffix}"
            suffix += 1
        used_keys.add(candidate)
        return candidate

    def _layer_array_for_tiff(self, layer: DataField | np.ndarray) -> np.ndarray:
        if isinstance(layer, DataField):
            return np.asarray(layer.data, dtype=np.float32)
        if isinstance(layer, np.ndarray):
            return image_to_uint8(layer)
        raise ValueError(f"Unsupported save layer type: {type(layer).__name__}")

    def _layer_array_for_npz(self, layer: DataField | np.ndarray) -> np.ndarray:
        if isinstance(layer, DataField):
            return np.asarray(layer.data)
        if isinstance(layer, np.ndarray):
            return np.asarray(layer)
        raise ValueError(f"Unsupported save layer type: {type(layer).__name__}")

    def _send_warning(self, message: str):
        fn = SaveImage._broadcast_warning_fn
        nid = SaveImage._current_node_id
        if fn and nid:
            fn(nid, message)

        return ()
