"""
I/O nodes: load and save images and SPM data.
"""

from __future__ import annotations
import os
import numpy as np
from pathlib import Path

from backend.node_registry import register_node
from backend.data_types import DataField, COLORMAPS, encode_preview, image_to_uint8
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


# ---------------------------------------------------------------------------
# LoadFile  (unified loader — replaces LoadImage + LoadSPM)
# ---------------------------------------------------------------------------

@register_node(display_name="Load File")
class LoadFile:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": ""}),
                "colormap": (list(COLORMAPS),),
            }
        }

    # Default outputs — overridden dynamically by the frontend for multi-channel files
    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "load"
    CATEGORY = "io"
    DESCRIPTION = (
        "Load any supported file. "
        "SPM formats (.gwy, .sxm, .ibw) provide calibrated dimensions; "
        "each channel gets its own output. "
        "Images (.png, .tiff, .jpg) and arrays (.npy, .npz) are loaded as uncalibrated fields."
    )

    # Set by execution engine for warning broadcast
    _broadcast_warning_fn = None
    _current_node_id = None

    def load(self, filename: str, colormap: str = "viridis"):
        if not filename or not filename.strip():
            raise ValueError("No file selected — use Browse to pick a file.")
        path = _resolve_path(filename)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"Expected a file, got a directory: {path}")

        ext = path.suffix.lower()

        if ext in _SPM_EXTENSIONS:
            fields = self._load_spm_all(path, ext)
            for f in fields:
                f.colormap = colormap
            return tuple(fields)

        # Image or array — uncalibrated, single output
        field = self._load_image_or_array(path, ext)
        field.colormap = colormap
        self._send_warning("Uncalibrated data — no physical dimensions.")
        return (field,)

    def _send_warning(self, message: str):
        fn = LoadFile._broadcast_warning_fn
        nid = LoadFile._current_node_id
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
# LoadDemo
# ---------------------------------------------------------------------------

def _list_demo_files() -> list[str]:
    """Return sorted list of demo filenames available in the demo/ directory."""
    if not DEMO_DIR.exists():
        return []
    return sorted(
        f.name for f in DEMO_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in _DEMO_EXTENSIONS
    )


@register_node(display_name="Load Demo File")
class LoadDemo:
    @classmethod
    def INPUT_TYPES(cls):
        choices = _list_demo_files() or ["(no demo files found)"]
        return {
            "required": {
                "name": (choices,),
                "colormap": (list(COLORMAPS),),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "load"
    CATEGORY = "io"
    DESCRIPTION = "Load a bundled demo file so you can try the app without providing your own data."

    def load(self, name: str, colormap: str = "viridis"):
        path = DEMO_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Demo file not found: {name}")

        loader = LoadFile()
        return loader.load(filename=str(path), colormap=colormap)


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
    CATEGORY = "io"
    DESCRIPTION = "Output a fractional (x, y) coordinate pair in [0, 1]."

    def process(self, x: float, y: float) -> tuple:
        return ((float(x), float(y)),)


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
    CATEGORY = "io"
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
        optional = {}
        for i in range(_MAX_SAVE_FIELDS):
            optional[f"field_{i}"] = ("DATA_FIELD",)
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": ""}),
                "format": (["TIFF", "NPZ"],),
            },
            "optional": optional,
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    CATEGORY = "io"
    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save one or more DATA_FIELD layers to a single file. "
        "Connect fields to the inputs — a new slot appears as each is filled. "
        "TIFF writes float32 multi-page; NPZ writes float64 named arrays. "
        "Click Save to write (does not auto-run)."
    )

    _broadcast_warning_fn = None
    _current_node_id = None

    def save(self, filename: str, format: str = "TIFF", **kwargs):
        # Collect connected fields in order
        fields = []
        for i in range(_MAX_SAVE_FIELDS):
            f = kwargs.get(f"field_{i}")
            if f is not None:
                fields.append(f)

        if not fields:
            raise ValueError("No fields connected — connect at least one DATA_FIELD input.")

        if not filename or not filename.strip():
            raise ValueError("No output path selected — use Browse to pick a location.")

        path = Path(filename)
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Force correct extension
        ext = ".tiff" if format == "TIFF" else ".npz"
        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)

        if format == "TIFF":
            self._save_tiff(path, fields)
        else:
            self._save_npz(path, fields)

        self._send_warning(f"Saved {len(fields)} layer(s) to {path.name}")
        return ()

    def _save_tiff(self, path: Path, fields: list[DataField]):
        from PIL import Image
        images = []
        for f in fields:
            images.append(Image.fromarray(f.data.astype(np.float32)))
        images[0].save(str(path), save_all=True, append_images=images[1:])

    def _save_npz(self, path: Path, fields: list[DataField]):
        arrays = {}
        for i, f in enumerate(fields):
            arrays[f"layer_{i}"] = f.data
        np.savez(str(path), **arrays)

    def _send_warning(self, message: str):
        fn = SaveImage._broadcast_warning_fn
        nid = SaveImage._current_node_id
        if fn and nid:
            fn(nid, message)

        return ()
